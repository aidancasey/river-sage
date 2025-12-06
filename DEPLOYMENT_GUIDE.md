# Deployment Guide - River Data Scraper & River Guru

Complete guide for deploying the Irish Rivers Data Scraper backend and River Guru web app.

## Quick Start

The simplest way to deploy everything:

```bash
# Deploy to production (backend + web app)
make deploy-prod
```

That's it! This single command will:
1. Build the Vue.js web application
2. Build the Lambda functions with SAM
3. Deploy infrastructure to AWS
4. Deploy the web app to S3
5. Display the deployment URLs

## Deployment Options

### Option 1: Makefile (Recommended)

```bash
# Production
make deploy-prod

# Development
make deploy-dev

# Staging
make deploy-staging

# View all available commands
make help
```

### Option 2: Deployment Script

```bash
# Production
./deploy.sh production

# Development
./deploy.sh dev

# Staging
./deploy.sh staging
```

### Option 3: Manual Step-by-Step

```bash
# 1. Build web app
cd web
npm install
npm run build
cd ..

# 2. Build Lambda functions
sam build

# 3. Deploy infrastructure
sam deploy --config-env production --no-confirm-changeset

# 4. Deploy web app
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
| production | river-data-scraper-prod | 3 min past every hour | river-data-ireland-prod | river-guru-web-production |

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

## First-Time Deployment

If deploying for the first time:

```bash
# 1. Configure AWS credentials
aws configure

# 2. Install dependencies
npm install -g aws-sam-cli
cd web && npm install && cd ..

# 3. Deploy
make deploy-prod

# 4. Note the output URLs
# - Web App URL
# - API Gateway URL
```

## Updating an Existing Deployment

To update an already-deployed environment:

```bash
# Update everything (recommended)
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
# Test API endpoints manually
curl "https://3su2ubk6j2.execute-api.eu-west-1.amazonaws.com/production/api/flow/latest"

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

Before deploying to production:

- [ ] AWS credentials configured
- [ ] SAM CLI installed
- [ ] Node.js 18+ installed
- [ ] Reviewed samconfig.toml settings
- [ ] Tested in dev/staging environment
- [ ] Verified API endpoint in web/.env
- [ ] Backup any existing data if needed
- [ ] Confirmed IAM permissions
- [ ] Ready to monitor CloudWatch logs

After deploying to production:

- [ ] Verify web app loads: http://river-guru-web-production.s3-website-eu-west-1.amazonaws.com
- [ ] Test API: `make test-api`
- [ ] Check data collection: Wait 1 hour, check S3 bucket
- [ ] Monitor CloudWatch logs for errors
- [ ] Set up CloudWatch alarms (already configured)
- [ ] Document deployment in team wiki/docs

## Support

For issues:
1. Check this guide
2. Review CloudWatch logs: `make logs ENV=production`
3. Check CloudFormation events in AWS Console
4. Create an issue in the repository
