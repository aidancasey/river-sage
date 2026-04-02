# Deployment Guide - River Data Scraper & River Guru

Complete guide for deploying the Irish Rivers Data Scraper backend and River Guru web app.

## Quick Start — CI/CD (Primary)

Push to `main` and GitHub Actions handles everything:

1. Runs tests (`pytest`) and validates the SAM template
2. Builds and deploys Lambda functions via SAM
3. Builds the Vue.js web app (fetches API URL from CloudFormation outputs)
4. Syncs the web app to S3

Auth uses **OIDC federation** with IAM role `github-actions-river-sage` — no AWS keys stored in GitHub.

See `.github/workflows/deploy.yml` for the full pipeline.

## Manual Deployment Options

For local deploys (e.g., debugging or when CI is unavailable):

### Option 1: Makefile

```bash
# Production
make deploy-prod

# Development
make deploy-dev

# View all available commands
make help
```

### Option 2: Manual Step-by-Step

```bash
# 1. Upload station config to S3
aws s3 cp config/data_sources.json \
  s3://river-data-ireland-prod/config/data_sources.json \
  --region eu-west-1 --content-type application/json

# 2. Build Lambda functions
sam build

# 3. Deploy infrastructure
sam deploy --config-env production --no-confirm-changeset

# 4. Build web app (requires VITE_API_BASE_URL in web/.env)
cd web && npm install && npm run build && cd ..

# 5. Deploy web app
aws s3 sync web/dist/ s3://river-guru-web-production/ \
  --region eu-west-1 \
  --delete \
  --cache-control "max-age=31536000,public"
```

## Environment-Specific Configuration

Each environment has different settings in [samconfig.toml](samconfig.toml):

| Environment | Stack Name | Schedule | S3 Bucket | Web Bucket |
|------------|------------|----------|-----------|------------|
| dev | river-data-scraper-dev | Every 6 hours | river-data-ireland-dev | river-guru-web-dev |
| staging | river-data-scraper-staging | Every 2 hours | river-data-ireland-staging | river-guru-web-staging |
| production | river-data-scraper-prod | 30 min past every hour | river-data-ireland-prod | river-guru-web-production |

## What Gets Deployed

### Backend Infrastructure (via AWS SAM/CloudFormation)

- **Lambda Functions**:
  - Data Collector: Scrapes PDF data from ESB Hydro
  - Data API: REST API for accessing river flow data

- **S3 Buckets**:
  - Data bucket: Stores raw PDFs, parsed JSON, aggregated data
  - Web bucket: Hosts the Vue.js static website

- **API Gateway**: REST API with CORS support

- **EventBridge**: Cron-based scheduling for data collection

- **IAM Roles**: Least-privilege access for Lambda functions

- **CloudWatch**: Log groups and alarms for monitoring

### Frontend Web App

- **Vue.js SPA**: Built with Vite, optimized for production
- **Static Assets**: Deployed to S3 with caching headers
- **API Integration**: Connects to API Gateway endpoints

## First-Time Setup

### CI/CD prerequisites (one-time)

These are already configured for this project:
- IAM OIDC provider for `token.actions.githubusercontent.com`
- IAM role `github-actions-river-sage` with trust policy scoped to `aidancasey/river-sage:main`
- `production` environment in GitHub repo settings

### Secrets in SSM Parameter Store

Twilio credentials are read by Lambda at runtime from SSM (not at deploy time):

| SSM Path | Type |
|---|---|
| `/river-data-scraper/twilio/account_sid` | SecureString |
| `/river-data-scraper/twilio/auth_token` | SecureString |
| `/river-data-scraper/twilio/whatsapp_from` | SecureString |
| `/river-data-scraper/alert-email` | String |

No redeploy needed after rotating a secret — Lambda picks up the new value on next cold start.

### Local development prerequisites

```bash
aws configure                          # AWS CLI credentials
pip install aws-sam-cli                # SAM CLI
cd web && npm install && cd ..         # Web app dependencies
cp web/.env.example web/.env           # Set VITE_API_BASE_URL
```

## Updating an Existing Deployment

The recommended approach is to push to `main` — CI handles the rest.

For manual updates:

```bash
# Update everything
make deploy-prod

# Or update just infrastructure
sam build && sam deploy --config-env production --no-confirm-changeset

# Or update just web app
cd web && npm run build && cd ..
make deploy-web ENV=production
```

## Verification

After deployment, verify everything works:

```bash
# Test API endpoints
make test-api

# View logs
make logs ENV=production

# Manually trigger data collection
make invoke ENV=production

# Check S3 bucket contents
aws s3 ls s3://river-data-ireland-prod/aggregated/

# Visit the web app
open http://river-guru-web-production.s3-website-eu-west-1.amazonaws.com
```

## Rollback

If something goes wrong, you can rollback the infrastructure:

```bash
# View stack events to identify the issue
aws cloudformation describe-stack-events \
  --stack-name river-data-scraper-prod \
  --region eu-west-1 \
  --max-items 20

# If needed, delete and redeploy
make teardown ENV=production
# Then redeploy
make deploy-prod
```

## Troubleshooting

### Build Failures

**Web app build fails:**
```bash
cd web
rm -rf node_modules package-lock.json
npm install
npm run build
```

**SAM build fails:**
```bash
make clean
sam build
```

### Deployment Failures

**Stack update fails:**
- Check CloudFormation console for detailed error messages
- Verify IAM permissions
- Check for resource name conflicts

**Web app deployment fails:**
- Verify S3 bucket exists: `aws s3 ls s3://river-guru-web-production/`
- Check AWS credentials: `aws sts get-caller-identity`
- Verify bucket permissions in CloudFormation template

### API Not Working

```bash
# Get the API Gateway URL from CloudFormation, then test
API_URL=$(aws cloudformation describe-stacks --stack-name river-data-scraper-prod \
  --region eu-west-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`RiverGuruApiUrl`].OutputValue' \
  --output text)
curl "$API_URL/api/flow/latest"

# Check Lambda logs
make logs ENV=production

# Test Lambda function directly
make invoke ENV=production
```

### Web App Not Loading

1. Check S3 bucket website hosting is enabled
2. Verify bucket policy allows public read access
3. Check browser console for CORS errors
4. Verify API endpoint in web/.env matches deployed API Gateway

## Cost Optimization

To minimize AWS costs:

```bash
# Use development environment for testing (6-hour scraping)
make deploy-dev

# For production, current costs are ~$1-2/month:
# - Lambda: ~$0.20/month (minimal execution time)
# - S3 Data: ~$0.50/month (with lifecycle policies)
# - S3 Web: ~$0.50/month (static hosting)
# - API Gateway: ~$0.10/month (low request volume)
# - Data Transfer: ~$0.20/month
```

## Cleaning Up

To completely remove all resources:

```bash
# This will delete EVERYTHING including all collected data!
make teardown ENV=production

# Confirm by typing 'yes' when prompted
```

## Production Deployment Checklist

CI/CD handles most of this automatically. For manual deploys:

Before deploying:

- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] SAM template validates (`sam validate --lint`)
- [ ] `web/.env` has correct `VITE_API_BASE_URL`

After deploying:

- [ ] Verify web app loads: https://www.theriverguru.com
- [ ] Test API: `make test-api`
- [ ] Check CloudWatch logs for errors
- [ ] CloudWatch alarms will email if anything fails (SNS topic configured)

## Support

For issues:
1. Check this guide
2. Review CloudWatch logs: `make logs ENV=production`
3. Check CloudFormation events in AWS Console
4. Create an issue in the repository
