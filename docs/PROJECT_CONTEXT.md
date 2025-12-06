# River Guru - Project Context

**For AI Assistants & New Developers**

This document provides essential context about the River Guru project to help you get up to speed quickly.

## Project Overview

**River Guru** is a low-cost serverless system for scraping and visualizing Irish river flow data from ESB Hydro. It consists of:
- **Backend**: AWS Lambda functions for data collection and API
- **Frontend**: Vue.js 3 single-page application
- **Data Source**: ESB Hydro PDF reports (Inniscarra Dam on River Lee)

**Current Status**: Phase 1 & 2 Complete ✅
- Data collection backend is deployed and running
- Web app is live and displaying real-time flow data

## Architecture

### Backend (AWS Serverless)

```
EventBridge (Cron) → Lambda (Collector) → S3 (Data Storage)
                                            ↓
                         Lambda (API) ← API Gateway → Web App
```

**Key Components**:
- **Data Collector Lambda**: `src/lambda_handler.py`
  - Runs every hour at 30 minutes past (UTC)
  - Downloads PDF from ESB Hydro
  - Parses flow data using pdfplumber
  - Stores: raw PDFs, parsed JSON, aggregated data in S3

- **Data API Lambda**: `api/data_api.py`
  - RESTful API for flow data
  - Endpoints: `/api/flow/latest`, `/api/flow/history`
  - CORS enabled for web app

### Frontend (Vue.js 3)

```
S3 Static Hosting → Vue.js SPA (Vite)
                    ↓
        Components: FlowStatus, FlowChart
                    ↓
              API Gateway (Backend)
```

**Location**: `web/`
- **Framework**: Vue.js 3 with Composition API
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Main Components**:
  - `FlowStatus.vue`: Current flow display with color-coded status
  - `FlowChart.vue`: Historical flow chart (24h, 7d, 30d, 90d views)

## Key Design Decisions

### 1. Scraping Schedule: 30 Minutes Past the Hour
**Rationale**: ESB Hydro publishes PDFs at approximately 26 minutes past each hour. Running at 30 minutes ensures we capture the same-hour data with minimal delay (~4 minutes).

**Important**: This is UTC time. Cron expression: `cron(30 * * * ? *)`

### 2. Unified Deployment with Makefile
**Rationale**: Single command deploys both backend infrastructure (SAM) and frontend (S3 sync).

```bash
make deploy-prod    # Deploys everything
make deploy-dev     # Development environment
make build          # Builds both Lambda and Vue.js
```

### 3. S3 Static Hosting (No CloudFront)
**Rationale**: Cost optimization. CloudFront adds ~$0.50/month minimum. Current traffic doesn't justify CDN costs.

**Trade-off**: Slightly higher latency for non-EU users, but acceptable for current usage.

### 4. No Auto-Refresh in Web App
**Decision**: Removed 5-minute auto-refresh feature.

**Rationale**: Users prefer manual refresh to avoid unexpected data reloads and unnecessary API calls.

### 5. Package-lock.json Committed
**Rationale**: Ensures reproducible builds across environments. Standard best practice for production apps.

## Important File Locations

### Backend
```
src/
├── lambda_handler.py          # Main data collector Lambda
├── config/settings.py         # Configuration management
├── connectors/http_connector.py  # HTTP downloads with retry
├── parsers/esb_hydro_parser.py   # PDF parsing logic
├── storage/s3_storage.py      # S3 operations
└── utils/
    ├── logger.py              # Structured logging
    └── retry.py               # Exponential backoff

api/
└── data_api.py                # RESTful API Lambda

tests/
├── test_*.py                  # Unit tests (pytest)
└── api/test_data_api.py       # API tests
```

### Frontend
```
web/
├── src/
│   ├── App.vue                # Main app component
│   ├── components/
│   │   ├── FlowStatus.vue     # Current flow display
│   │   └── FlowChart.vue      # Historical chart
│   ├── services/api.js        # API client
│   └── utils/date.js          # Date formatting
├── .env                       # Environment config (GITIGNORED!)
├── .env.example               # Template for contributors
└── package.json               # Dependencies
```

### Infrastructure
```
template.yaml                  # SAM/CloudFormation template
samconfig.toml                 # SAM deployment config
Makefile                       # Build automation
deploy.sh                      # Deployment wrapper script
```

### Documentation
```
README.md                      # Main documentation
CONTRIBUTING.md                # Contribution guidelines
DEPLOYMENT_GUIDE.md            # Detailed deployment instructions
LICENSE                        # CC BY-NC 4.0 License
docs/
├── PROJECT_CONTEXT.md         # This file
└── history/                   # Archived planning docs
```

## Development Workflow

### Local Setup

1. **Backend Setup**:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest  # Run tests
```

2. **Frontend Setup**:
```bash
cd web
npm install
npm run dev  # Start dev server on http://localhost:5173
```

3. **Environment Variables**:
```bash
# Backend: Uses AWS credentials from ~/.aws/
# Frontend: Copy web/.env.example to web/.env
# Set VITE_API_BASE_URL to your API Gateway URL
```

### Common Commands

```bash
# Development
make dev-web                   # Start Vue.js dev server

# Testing
pytest                         # Run Python tests
make test-api                  # Test API endpoints

# Building
make build                     # Build Lambda + Vue.js
make build-web                 # Build Vue.js only
make build-lambda              # Build Lambda only

# Deployment
make deploy-prod               # Deploy to production
make deploy-dev                # Deploy to development
make deploy-staging            # Deploy to staging

# Monitoring
make logs ENV=production       # Tail Lambda logs
make invoke ENV=production     # Manually trigger collector

# Cleanup
make clean                     # Remove build artifacts
make teardown ENV=production   # Delete CloudFormation stack (DANGER!)
```

## Deployment Details

### Production Environment

**Stack Name**: `river-data-scraper-prod`
**Region**: `eu-west-1` (Ireland)
**Schedule**: Every hour at 30 minutes past (UTC)

**Live URLs**:
- Web App: http://river-guru-web-production.s3-website-eu-west-1.amazonaws.com
- API: https://3su2ubk6j2.execute-api.eu-west-1.amazonaws.com/production

**AWS Resources**:
- Data Collector Lambda: `river-data-scraper-prod-collector`
- Data API Lambda: `river-data-scraper-prod-data-api`
- Data S3 Bucket: `river-data-ireland-prod`
- Web S3 Bucket: `river-guru-web-production`

**S3 Data Structure**:
```
river-data-ireland-prod/
├── raw/                       # Original PDFs
│   └── inniscarra/
│       └── YYYYMMDD_HHMMSS.pdf
├── parsed/                    # Parsed JSON
│   └── inniscarra/
│       └── YYYYMMDD_HHMMSS.json
└── aggregated/                # Latest data
    ├── inniscarra_latest.json
    └── inniscarra_history.json
```

### Cost Estimate

**Monthly Operating Costs**: ~$0.02/month

- Lambda: Free tier (720 invocations × 30s × 256MB)
- EventBridge: Free tier
- S3 Storage: ~500MB = $0.01
- S3 Requests: ~1,500 = $0.01
- CloudWatch Logs: Free tier

**Scaling**: With 10 stations for 1 year: ~$0.15/month

## Known Gotchas

### 1. ESB Hydro PDF Publishing Time
- PDFs published at **~26 minutes past each hour**
- Our scraper runs at **30 minutes past**
- This timing is crucial for capturing same-hour data

### 2. Environment Files (.env)
- **MUST be in .gitignore** (already configured)
- Never commit actual `.env` files to GitHub
- Use `.env.example` for templates
- Frontend requires: `VITE_API_BASE_URL=<your-api-url>`

### 3. Package Lock Files
- `web/package-lock.json` **should be committed** (not ignored)
- Ensures reproducible builds
- Recently changed from ignored to tracked

### 4. SAM Build Process
- Always run `make build` before `sam deploy`
- SAM packages dependencies into `.aws-sam/build/`
- Build artifacts are gitignored

### 5. CORS Configuration
- API Gateway has CORS enabled for all origins (`*`)
- Required for S3-hosted frontend to call API
- Configured in `template.yaml` and `api/data_api.py`

### 6. Lambda Cold Starts
- First request after inactivity may be slow (~2-3 seconds)
- Subsequent requests are fast (<200ms)
- Consider provisioned concurrency if this becomes an issue

### 7. Timezone Confusion
- EventBridge cron runs in **UTC**
- Display times on frontend use **user's local timezone**
- ESB data timestamps are in **Irish time (IST/GMT)**

## Testing

### Run All Tests
```bash
pytest                          # All tests
pytest -v                       # Verbose
pytest --cov=src tests/         # With coverage
```

### Test Specific Components
```bash
pytest tests/test_http_connector.py
pytest tests/test_esb_hydro_parser.py
pytest tests/api/test_data_api.py
```

### Manual Testing
```bash
# Test API endpoints
make test-api

# Manually trigger data collection
make invoke ENV=production

# Check S3 for latest data
aws s3 ls s3://river-data-ireland-prod/aggregated/

# Download and inspect latest data
aws s3 cp s3://river-data-ireland-prod/aggregated/inniscarra_latest.json - | jq
```

## Monitoring & Debugging

### CloudWatch Logs

**Data Collector Logs**:
```
/aws/lambda/river-data-scraper-prod-collector
```

**Data API Logs**:
```
/aws/lambda/river-data-scraper-prod-data-api
```

**View Logs**:
```bash
make logs ENV=production        # Tail logs in real-time
```

### CloudWatch Insights Queries

**Find Errors**:
```sql
fields @timestamp, @message
| filter level = "ERROR"
| sort @timestamp desc
```

**Success Rate**:
```sql
stats count() as total,
      sum(context.success) as successful
by bin(5m)
```

### Common Issues

**Problem**: Lambda function times out
**Solution**: Check network connectivity to ESB Hydro, increase timeout in template.yaml

**Problem**: PDF parsing fails
**Solution**: Check if ESB changed PDF format, update parser in `esb_hydro_parser.py`

**Problem**: Web app shows stale data
**Solution**: Check S3 bucket for recent files, verify Lambda execution logs

**Problem**: CORS errors in browser
**Solution**: Verify API Gateway CORS configuration, check API response headers

## Future Roadmap

### Phase 3: Enhanced Data Collection
- Add more river stations (multiple dams)
- Integrate weather data from Met Éireann
- Correlate rainfall with flow data
- Data validation and quality checks
- Multi-station support in web app

### Phase 4: Advanced Features
- User accounts and preferences
- Flow alert notifications (email/SMS)
- Predictive flow analytics (ML models)
- PWA capabilities (offline mode, install to home screen)
- Mobile native apps (iOS/Android)
- Data export (CSV, JSON, PDF reports)

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Code style guidelines
- Pull request process
- Testing requirements
- How to add new river stations

## License

**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** - See [LICENSE](../LICENSE) for details.

**Permissions**: Share, adapt, use for personal/educational purposes, fork and contribute.

**Restrictions**: Attribution required, NO commercial use allowed. Contact maintainer for commercial licensing.

## Quick Reference

### Project URLs
- Production Web: http://river-guru-web-production.s3-website-eu-west-1.amazonaws.com
- Production API: https://3su2ubk6j2.execute-api.eu-west-1.amazonaws.com/production
- GitHub: (will be added after initial push)

### Key Contacts
- Data Source: ESB Hydro (http://www.esbhydro.ie/)
- AWS Region: eu-west-1 (Ireland)

### Tech Stack Summary
- **Backend**: Python 3.9, AWS Lambda, boto3, pdfplumber
- **Frontend**: Vue.js 3, Vite, Tailwind CSS, Chart.js
- **Infrastructure**: AWS SAM, CloudFormation
- **Storage**: Amazon S3
- **API**: API Gateway (REST)
- **Scheduling**: EventBridge (cron)
- **Monitoring**: CloudWatch Logs & Metrics

---

**Last Updated**: December 6, 2024
**Project Phase**: Phase 2 Complete (Data Collection + Web App)
**Status**: Production Deployed & Running

**Generated with Claude Code** - Update this file as the project evolves!
