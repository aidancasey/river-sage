# CLAUDE.md — River Data Scraper

Project context and hard-won operational knowledge for working with this repo.

## Project overview

Three Lambda functions (arm64, python3.13, eu-west-1) deployed via AWS SAM:
- `river-data-scraper-collector` — hourly EventBridge trigger, scrapes ESB Hydro PDF + waterlevel.ie API, writes to S3, sends WhatsApp alerts via Twilio
- `river-data-scraper-alerts-api` — REST API for managing WhatsApp alert subscriptions
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

### Secrets

Twilio credentials live in **SSM Parameter Store** (eu-west-1) as `SecureString`. The Lambda reads them **at runtime** via `_get_ssm_or_env()` in `lambda_handler.py` — they are NOT resolved at deploy time.

| SSM path | What it is |
|---|---|
| `/river-data-scraper/twilio/account_sid` | Twilio Account SID |
| `/river-data-scraper/twilio/auth_token` | Twilio Auth Token |
| `/river-data-scraper/twilio/whatsapp_from` | Twilio WhatsApp sender number |
| `/river-data-scraper/alert-email` | Email for CloudWatch alarm notifications |

The template passes SSM **paths** as `*_SSM` env vars (e.g., `TWILIO_ACCOUNT_SID_SSM`). The Lambda calls `ssm:GetParameter` with `WithDecryption=True` on first invocation and caches the result for warm reuse. For local development, set plain `TWILIO_ACCOUNT_SID` etc. in your environment.

To rotate a secret:
```bash
aws ssm put-parameter --name /river-data-scraper/twilio/auth_token \
  --value "new-value" --type SecureString --region eu-west-1 --overwrite
# No redeploy needed — Lambda picks up new value on next cold start
```

### Monitoring

CloudWatch alarms for Lambda errors and throttles publish to SNS topic `${StackName}-alarms`, which emails the address in `/river-data-scraper/alert-email`.

## Lambda package size limit

Lambda's 262MB limit applies to **code + all layers combined**. The ADOT/OTEL layer alone was ~219MB. OTEL/Dash0 observability has been removed — do not re-add Lambda layers without checking the combined size first.

Check package sizes after build:
```bash
du -sh .aws-sam/build/*/
du -sh .aws-sam/build/RiverDataCollectorFunction/* | sort -rh | head -15
```

The collector package should be ~60MB. If it bloats again, the usual culprits are:
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
aws cloudformation describe-stacks --stack-name river-data-scraper \
  --region eu-west-1 --query 'Stacks[0].StackStatus'

# 2. Confirm no OTEL layers and SSM paths are set (not raw credentials)
aws lambda get-function-configuration --function-name river-data-scraper-collector \
  --region eu-west-1 --query '{Layers:Layers,TwilioSSM:Environment.Variables.TWILIO_ACCOUNT_SID_SSM}'

# 3. Live invocation test (confirms all 7 stations collect successfully)
aws lambda invoke --function-name river-data-scraper-collector \
  --region eu-west-1 --log-type Tail /tmp/response.json \
  | python3 -c "import json,sys,base64; d=json.load(sys.stdin); print(base64.b64decode(d['LogResult']).decode()[-2000:])"
```

The invocation response should show `"success_count": 7, "total_count": 7`.
