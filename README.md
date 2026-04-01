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

### Build

```bash
sam build --no-cached
```

The build uses `BuildMethod: makefile` for the Collector and Alerts API functions — SAM's Python pip builder ignores `RequirementsFilename` when `CodeUri` points to the project root. The Makefile targets install only the deps each function needs, cross-compiled for Linux arm64 Python 3.13.

Check package sizes after building — the Lambda + layers combined must stay under 262MB:

```bash
du -sh .aws-sam/build/*/
```

### Deploy

```bash
sam deploy --no-confirm-changeset
```

`samconfig.toml` has all non-secret parameters pre-configured for production. No extra flags needed.

### Secrets

Twilio credentials are stored in **AWS SSM Parameter Store** and resolved by CloudFormation at deploy time — they are not stored in any local file or committed to git.

| SSM Path | Description |
|---|---|
| `/river-data-scraper/twilio/account_sid` | Twilio Account SID |
| `/river-data-scraper/twilio/auth_token` | Twilio Auth Token |
| `/river-data-scraper/twilio/whatsapp_from` | WhatsApp sender number |

To rotate a secret:
```bash
aws ssm put-parameter --name /river-data-scraper/twilio/auth_token \
  --value "new-value" --type SecureString --region eu-west-1 --overwrite
sam deploy --no-confirm-changeset
```

### Web App

```bash
cd web && npm install && npm run build
aws s3 sync dist/ s3://river-guru-web-production/ --region eu-west-1 --delete
```

Or deploy everything (infrastructure + web app) in one command:

```bash
make deploy-prod
```

## Production Environment

**Region**: `eu-west-1`  
**Stack**: `river-data-scraper`

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

CloudWatch Alarms are configured for Lambda errors and throttles on the collector function.

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
