# Irish Rivers Data Scraper

A low-cost, serverless system for aggregating water data from Irish rivers, including flow rates from ESB Hydro and water level/temperature data from waterlevel.ie.

## Screenshots

![River Guru Web App](docs/screenshots/app-screenshot.png)

*River Guru displays real-time data from Inniscarra Dam (flow) and Waterworks Weir (water level & temperature) with interactive historical charts*

## Features

- **Multiple Data Sources**: ESB Hydro flow data (PDF) and waterlevel.ie water level/temperature (CSV API)
- **7 Active Stations**: Inniscarra Dam, Lee Waterworks, Blackwater Fermoy, Blackwater Mallow, Suir Golden, Owenboy, Bandon Curranure
- **Serverless Architecture**: AWS Lambda (arm64, Python 3.13), minimal operating costs (<$5/month)
- **Hourly Data Collection**: EventBridge trigger at 30 minutes past the hour
- **River Guru Web App**: Mobile-first Vue.js SPA with real-time flow display and historical charts
- **WhatsApp Flow Alerts**: Daily opt-in alerts via Twilio when Inniscarra flow changes by >2 m³/s
- **Zero-Database Design**: All state (data + alert subscriptions) stored as JSON/CSV in S3

## Architecture

```
EventBridge (hourly)
       │
       ▼
Collector Lambda ──► S3 (raw PDFs/CSVs, parsed JSON, aggregated latest)
  • ESB Hydro PDF      │
  • waterlevel.ie API  └──► Twilio WhatsApp API ──► Subscribers' phones
                                (flow change > 2 m³/s)

Users (browser)
       │ HTTPS
       ▼
API Gateway
  ├── GET /api/flow/latest   ──► Data API Lambda ──► S3
  ├── GET /api/flow/history  ──► Data API Lambda ──► S3
  ├── POST /api/alerts/register ──► Alerts API Lambda ──► S3
  ├── POST /api/alerts/optin    ──► Alerts API Lambda ──► S3
  └── POST /api/alerts/status   ──► Alerts API Lambda ──► S3

Web App (Vue.js SPA) hosted on S3 static website
```

## Project Structure

```
river-data-scraper/
├── .github/workflows/deploy.yml  # CI/CD pipeline (push to main → production)
├── template.yaml                 # SAM/CloudFormation template
├── samconfig.toml                # SAM deploy configuration (no secrets)
├── Makefile                      # Build and deploy automation
├── requirements-collector.txt    # Collector Lambda deps (no Twilio/boto3)
├── requirements-alerts.txt       # Alerts API Lambda deps (Twilio only, no boto3)
│
├── src/                          # Collector Lambda
│   ├── lambda_handler.py
│   ├── config/settings.py
│   ├── connectors/http_connector.py
│   ├── notifications/whatsapp_notifier.py
│   ├── parsers/
│   │   ├── esb_hydro_parser.py
│   │   └── waterlevel_parser.py
│   ├── storage/s3_storage.py
│   └── utils/
│       ├── logger.py
│       └── retry.py
│
├── api/                          # API Lambdas
│   ├── data_api.py
│   ├── alerts_api.py
│   └── requirements.txt          # Data API deps (empty — boto3 from runtime)
│
└── web/                          # Vue.js web app
    └── src/
        ├── components/
        │   ├── FlowStatus.vue
        │   ├── FlowChart.vue
        │   ├── WaterLevelStatus.vue
        │   ├── WaterLevelChart.vue
        │   └── AlertSubscription.vue
        └── services/api.js
```

## Prerequisites

- Python 3.11+
- AWS SAM CLI
- AWS CLI configured (`aws configure`)
- Node.js 18+ and npm (for the web app)

## Local Development

```bash
# Create virtual environment
python3 -m venv venv && source venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v
```

## Deployment

### CI/CD (Primary)

Pushing to `main` triggers a GitHub Actions pipeline (`.github/workflows/deploy.yml`):

1. **test** — runs `pytest tests/ -v`
2. **validate** — runs `sam validate --lint`
3. **deploy** — builds and deploys Lambda functions, then builds and deploys the web app

Auth uses OIDC federation with IAM role `github-actions-river-sage` — no long-lived AWS keys.

### Manual Deploy

For local deploys (e.g., debugging):

```bash
make deploy-prod   # builds and deploys everything
```

Or step by step:

```bash
sam build --no-cached
sam deploy --config-env production --no-confirm-changeset
cd web && npm install && npm run build
aws s3 sync dist/ s3://river-guru-web-production/ --region eu-west-1 --delete
```

### Secrets

Twilio credentials are stored in **AWS SSM Parameter Store** as `SecureString` and read by the Lambda **at runtime** (not at deploy time). No secrets are stored in source code, environment variables, or GitHub.

| SSM Path | Description |
|---|---|
| `/river-data-scraper/twilio/account_sid` | Twilio Account SID |
| `/river-data-scraper/twilio/auth_token` | Twilio Auth Token |
| `/river-data-scraper/twilio/whatsapp_from` | WhatsApp sender number |
| `/river-data-scraper/alert-email` | Email for CloudWatch alarm notifications |

To rotate a secret:
```bash
aws ssm put-parameter --name /river-data-scraper/twilio/auth_token \
  --value "new-value" --type SecureString --region eu-west-1 --overwrite
# No redeploy needed — Lambda picks up new value on next cold start
```

## Production Environment

**Region**: `eu-west-1`  
**Stack**: `river-data-scraper-prod`

| Resource | Name |
|---|---|
| Collector Lambda | `river-data-scraper-collector` |
| Data API Lambda | `river-data-scraper-data-api` |
| Alerts API Lambda | `river-data-scraper-alerts-api` |
| Data S3 Bucket | `river-data-ireland-prod` |
| Web App S3 Bucket | `river-guru-web-production` |
| API Gateway | `https://pyubfyqre6.execute-api.eu-west-1.amazonaws.com/production` |
| Web App | `http://river-guru-web-production.s3-website-eu-west-1.amazonaws.com` |

**Useful commands:**

```bash
# Tail live logs
sam logs --tail --stack-name river-data-scraper --region eu-west-1

# Manually trigger a collection run
aws lambda invoke --function-name river-data-scraper-collector \
  --region eu-west-1 /tmp/response.json && cat /tmp/response.json | jq .

# Check latest data in S3
aws s3 cp s3://river-data-ireland-prod/aggregated/inniscarra_latest.json - | jq .

# Check stack status
aws cloudformation describe-stacks --stack-name river-data-scraper \
  --region eu-west-1 --query 'Stacks[0].StackStatus'
```

## Monitoring

Logs are structured JSON, queryable in CloudWatch Insights:

```
/aws/lambda/river-data-scraper-collector
/aws/lambda/river-data-scraper-data-api
/aws/lambda/river-data-scraper-alerts-api
```

Example query — find errors by station:
```sql
fields @timestamp, context.station_id, message
| filter level = "ERROR"
| sort @timestamp desc
```

CloudWatch Alarms for Lambda errors and throttles publish to an SNS topic that emails the address stored in `/river-data-scraper/alert-email` (SSM Parameter Store).

## Roadmap

- [x] ESB Hydro PDF parsing (Inniscarra Dam flow)
- [x] waterlevel.ie CSV integration (6 additional stations)
- [x] S3 storage (raw, parsed, aggregated)
- [x] River Guru web app (Vue.js, mobile-first)
- [x] API Gateway + Data API Lambda
- [x] WhatsApp flow alerts (Twilio, daily opt-in, threshold detection)
- [x] Alerts API Lambda + AlertSubscription component
- [ ] Additional waterlevel.ie stations
- [ ] Met Éireann rainfall correlation
- [ ] Raw file cleanup (30–90 day S3 lifecycle)
- [ ] Apple Watch / watchOS Shortcuts endpoint

## License

Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) — see [LICENSE](LICENSE).

## Data Attribution

Water level and temperature data from [waterlevel.ie](https://waterlevel.ie/), provided by the Office of Public Works (OPW) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Flow data courtesy of [ESB Hydro](http://www.esbhydro.ie/).
