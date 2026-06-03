# CLAUDE.md — River Data Scraper

Project context and hard-won operational knowledge for working with this repo.

## Documentation rule

Whenever you make a code or configuration change, check whether any of the following files need updating and update them in the same commit:
- `README.md` — project overview, prerequisites, commands, production resource names
- `DEPLOYMENT_GUIDE.md` — deployment steps, environment config table, troubleshooting
- `CLAUDE.md` — operational knowledge, stack names, package sizes, SSM paths
- `IMPROVEMENTS.md` — mark items complete when done

If a change affects stack names, Lambda function names, S3 bucket names, SSM paths, environment variables, schedules, package sizes, or deployment steps — update the relevant doc. Do not leave documentation stale.

## Project overview

Three Lambda functions (arm64, python3.13, eu-west-1) deployed via AWS SAM:
- `river-data-scraper-collector` — hourly EventBridge trigger, scrapes ESB Hydro PDF + waterlevel.ie API, writes to S3, sends SMS alerts via Amazon SNS
- `river-data-scraper-alerts-api` — REST API for managing SMS alert subscriptions
- `river-data-scraper-data-api` — REST API for serving river flow data to the web app

## SAM build

The Python pip builder ignores `RequirementsFilename` in `BuildProperties` when `CodeUri` points to the project root — it always falls back to `requirements.txt`. Both functions using `CodeUri: .` therefore use **`BuildMethod: makefile`** with explicit targets in `Makefile`.

```bash
sam build --no-cached   # always use --no-cached when debugging package size issues
```

The Makefile targets install for the Lambda target platform (Linux arm64, Python 3.13):
```makefile
build-RiverDataCollectorFunction:
    python3 -m pip install -r requirements-collector.txt \
        --target "$(ARTIFACTS_DIR)" \
        --platform manylinux2014_aarch64 \
        --implementation cp \
        --python-version 3.13 \
        --only-binary=:all: ...
```

**Do not add `boto3`/`botocore` to any requirements file** — Lambda runtime provides them.

## CI/CD

Pushing to `main` triggers GitHub Actions (`.github/workflows/deploy.yml`):
1. `test` — runs `pytest tests/ -v`
2. `validate` — runs `sam validate --lint`
3. `deploy` — `sam build` → `sam deploy` → build web app → sync to S3

Auth uses **OIDC federation** — IAM role `github-actions-river-sage` with trust scoped to `aidancasey/river-sage:main`. No long-lived AWS keys stored anywhere.

## SAM deploy

For manual deploys (CI handles this automatically):

```bash
sam deploy --config-env production --no-confirm-changeset
```

`samconfig.toml` has all non-secret parameters pre-configured for production. It is safe to commit — **no secrets are stored in it**.

### Secrets & configuration

SMS flow alerts are sent via **Amazon SNS** using the collector's IAM role (`sns:Publish`) — there are **no SMS credentials**. The only SSM parameter is the alarm email, resolved by CloudFormation at deploy time via `{{resolve:ssm:/river-data-scraper/alert-email}}`.

| SSM path | What it is |
|---|---|
| `/river-data-scraper/alert-email` | Email for CloudWatch alarm notifications |

`lambda_handler.py` still has a generic `_get_ssm_or_env()` helper (reads a `*_SSM` env var, calls `ssm:GetParameter` with `WithDecryption=True`, caches per cold start), but no secrets are wired through it since the Twilio→SNS migration.

To change the alarm email:
```bash
aws ssm put-parameter --name /river-data-scraper/alert-email \
  --value "new@example.com" --type String --region eu-west-1 --overwrite
# Redeploy to update the SNS topic subscription (resolved at deploy time)
```

### Monitoring

CloudWatch alarms for Lambda errors and throttles publish to SNS topic `${StackName}-alarms`, which emails the address in `/river-data-scraper/alert-email`.

## Data sources config

Station configuration lives in `config/data_sources.json` (committed to git). CI uploads it to `s3://river-data-ireland-prod/config/data_sources.json` on every deploy. The Lambda reads it at startup via the `DATA_SOURCES_S3_KEY` env var.

To add or change a station: edit `config/data_sources.json` and push to `main`. No CloudFormation deploy needed — takes effect on next Lambda invocation.

## Lambda package size limit

Lambda's 262MB limit applies to **code + all layers combined**. The ADOT/OTEL layer alone was ~219MB. OTEL/Dash0 observability has been removed — do not re-add Lambda layers without checking the combined size first.

Check package sizes after build:
```bash
du -sh .aws-sam/build/*/
du -sh .aws-sam/build/RiverDataCollectorFunction/* | sort -rh | head -15
```

The collector package should be ~90MB. The alerts-api package no longer bundles Twilio (~30MB saved by the SNS migration — it now has no third-party deps). If a package bloats again, the usual culprits are:
- `web/` directory being copied (CodeUri: . copies everything not in .samignore)
- `boto3`/`botocore` bundled unnecessarily
- Dependencies bleeding in from the root `requirements.txt`

## CloudFormation stack state

Stack name: `river-data-scraper-prod` (eu-west-1)

If the stack is in `UPDATE_ROLLBACK_COMPLETE`, it is stable — `sam deploy` will work, it just won't include whatever resource failed. Fix the underlying issue first, then deploy.

The EventBridge hourly schedule (`RiverDataCollectorFunctionHourlySchedule`) is managed by CloudFormation. If it ever needs to be recreated manually as a workaround, **delete the manual rule before the next `sam deploy`** to avoid a naming conflict:
```bash
aws events remove-targets --rule <rule-name> --ids collector --region eu-west-1
aws events delete-rule --name <rule-name> --region eu-west-1
```

## Verifying a deployment

After deploying, run these checks:

```bash
# 1. Stack status
aws cloudformation describe-stacks --stack-name river-data-scraper-prod \
  --region eu-west-1 --query 'Stacks[0].StackStatus'

# 2. Confirm no OTEL layers are attached
aws lambda get-function-configuration --function-name river-data-scraper-collector \
  --region eu-west-1 --query '{Layers:Layers}'

# 3. Live invocation test (confirms all 7 stations collect successfully)
aws lambda invoke --function-name river-data-scraper-collector \
  --region eu-west-1 --log-type Tail /tmp/response.json \
  | python3 -c "import json,sys,base64; d=json.load(sys.stdin); print(base64.b64decode(d['LogResult']).decode()[-2000:])"
```

The invocation response should show `"success_count": 7, "total_count": 7`.
