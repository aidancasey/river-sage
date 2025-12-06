# AWS SAM Setup Complete

## What Changed?

Your river data scraper has been converted from manual deployment scripts to **AWS SAM (Serverless Application Model)** for easy deployment and complete teardown.

## New Files Created

### 1. [template.yaml](template.yaml) - Infrastructure as Code

Defines all AWS resources:
- **Lambda Function** with Python 3.9 on ARM64 (Graviton2)
- **S3 Bucket** with encryption, versioning, and lifecycle policies
- **EventBridge Rule** for hourly scheduling
- **IAM Role** with S3 and CloudWatch permissions
- **CloudWatch Alarms** for error monitoring
- **CloudWatch Log Group** with 30-day retention

### 2. [samconfig.toml](samconfig.toml) - Deployment Configuration

Pre-configured environments:
- **Development**: Scrapes every 6 hours, bucket `river-data-ireland-dev`
- **Staging**: Scrapes every 2 hours, bucket `river-data-ireland-staging`
- **Production**: Scrapes every 1 hour, bucket `river-data-ireland-prod`

### 3. [.samignore](.samignore) - Build Exclusions

Excludes tests, docs, and dev files from Lambda deployment package.

### 4. [DEPLOYMENT.md](DEPLOYMENT.md) - Complete Deployment Guide

Step-by-step instructions for:
- Installing SAM CLI
- Deploying to AWS
- Tearing down resources
- Monitoring and troubleshooting
- CI/CD integration

## Benefits of SAM

### ✅ Easy Deployment

```bash
# Deploy everything with one command
sam build && sam deploy --guided

# Update code quickly
sam sync --code
```

### ✅ Complete Teardown

```bash
# Delete ALL resources (Lambda, S3, IAM, EventBridge, CloudWatch)
sam delete

# All data is removed cleanly
```

### ✅ Multiple Environments

```bash
# Deploy to dev
sam build && sam deploy --config-env dev

# Deploy to production
sam build && sam deploy --config-env production

# Teardown dev
sam delete --config-env dev
```

### ✅ Local Testing

```bash
# Test Lambda function locally (no AWS deployment needed)
sam local invoke

# Watch for code changes
sam sync --watch
```

### ✅ Infrastructure as Code

All resources defined in `template.yaml`:
- Version controlled
- Repeatable deployments
- Easy to review and modify
- No manual AWS Console clicking

## What's Included in the Infrastructure?

When you deploy with SAM, it creates:

### Core Services

1. **Lambda Function**
   - Name: `{stack-name}-collector`
   - Runtime: Python 3.9 (ARM64)
   - Memory: 256 MB
   - Timeout: 120 seconds
   - Schedule: Hourly (configurable)

2. **S3 Bucket**
   - Name: `river-data-ireland-{env}`
   - Encryption: AES256
   - Versioning: Enabled
   - Lifecycle Rules:
     - Raw PDFs → Glacier after 90 days
     - Parsed JSON → Intelligent-Tiering after 30 days
     - Delete old versions after 90 days

3. **EventBridge Rule**
   - Schedule: `rate(1 hour)` (production)
   - Automatically triggers Lambda

4. **IAM Role**
   - S3 read/write permissions
   - CloudWatch Logs permissions
   - Follows principle of least privilege

### Monitoring

5. **CloudWatch Log Group**
   - Location: `/aws/lambda/{function-name}`
   - Retention: 30 days
   - Structured JSON logging

6. **CloudWatch Alarms**
   - Lambda errors alarm
   - Lambda throttling alarm
   - Can integrate with SNS for notifications

## Cost Comparison

**Before (Manual)**: Risk of forgetting resources, paying for orphaned resources

**After (SAM)**: Clean teardown, predictable costs

### Estimated Costs (Production, Hourly Scraping)

| Resource | Monthly Cost |
|----------|--------------|
| Lambda | $0.00 (free tier) |
| S3 Storage | $0.0025 |
| S3 Requests | $0.01 |
| EventBridge | $0.00 (free tier) |
| CloudWatch | $0.00 (free tier) |
| **Total** | **~$0.01-0.02/month** |

### ARM64 Savings

Using ARM64 (Graviton2) saves 20% on Lambda costs compared to x86_64.

## Before You Deploy

### 1. Install SAM CLI

**macOS:**
```bash
brew install aws-sam-cli
```

**Linux:**
```bash
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
```

**Verify:**
```bash
sam --version
```

### 2. Configure AWS Credentials

```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=eu-west-1
```

### 3. Choose Your S3 Bucket Name

S3 bucket names must be globally unique. Edit [samconfig.toml](samconfig.toml) if needed:

```toml
parameter_overrides = [
    "S3BucketName=river-data-ireland-yourname-prod"
]
```

## Quick Start

### Deploy to Production

```bash
# Navigate to project directory
cd /Users/aidan.casey/code/guru/river-data-scraper

# Build and deploy (first time - interactive)
sam build && sam deploy --guided

# Subsequent deploys
sam build && sam deploy
```

The `--guided` flag will ask you:
- ✅ Stack name: `river-data-scraper`
- ✅ Region: `eu-west-1`
- ✅ Confirm IAM changes: `Y`
- ✅ Save to samconfig.toml: `Y`

### Deploy to Development

```bash
sam build && sam deploy --config-env dev
```

### Teardown Everything

```bash
# Delete production
sam delete

# Delete development
sam delete --config-env dev --stack-name river-data-scraper-dev
```

**⚠️ WARNING**: This removes the S3 bucket and all stored data!

## Deployment Output

After successful deployment, SAM outputs:

```
CloudFormation outputs from deployed stack
-------------------------------------------------------------------------
Outputs
-------------------------------------------------------------------------
Key                 RiverDataCollectorFunctionArn
Description         ARN of the Lambda function
Value               arn:aws:lambda:eu-west-1:123456789:function:river-data-scraper-collector

Key                 RiverDataBucketName
Description         Name of the S3 bucket for river data
Value               river-data-ireland-prod

Key                 S3ConsoleUrl
Description         URL to S3 bucket in AWS Console
Value               https://s3.console.aws.amazon.com/s3/buckets/river-data-ireland-prod

Key                 LambdaConsoleUrl
Description         URL to Lambda function in AWS Console
Value               https://console.aws.amazon.com/lambda/...

Key                 CloudWatchLogsUrl
Description         URL to CloudWatch Logs
Value               https://console.aws.amazon.com/cloudwatch/...
-------------------------------------------------------------------------
```

Click the URLs to view your resources in AWS Console!

## Monitoring Your Deployment

### View Real-Time Logs

```bash
# Tail logs in real-time
sam logs --tail

# View last 10 minutes
sam logs --start-time '10min ago'
```

### Check S3 Data

```bash
# List all files
aws s3 ls s3://river-data-ireland-prod/ --recursive

# Download latest data
aws s3 cp s3://river-data-ireland-prod/aggregated/inniscarra_latest.json .
cat inniscarra_latest.json | jq
```

### Invoke Lambda Manually

```bash
# Test your Lambda function
aws lambda invoke \
  --function-name river-data-scraper-collector \
  response.json

# View response
cat response.json | jq
```

## Customizing Your Deployment

### Change Scraping Frequency

Edit [samconfig.toml](samconfig.toml):

```toml
# Every 30 minutes
"ScheduleExpression=rate(30 minutes)"

# Every 6 hours
"ScheduleExpression=rate(6 hours)"

# Daily at 9 AM UTC
"ScheduleExpression=cron(0 9 * * ? *)"
```

### Add More River Stations

Edit [template.yaml](template.yaml) environment variables:

```yaml
Environment:
  Variables:
    # Add more data sources
    DATA_SOURCE_2_NAME: "Shannon"
    DATA_SOURCE_2_URL: "http://..."
```

Then modify [src/config/settings.py](src/config/settings.py) to load multiple sources.

### Change Memory or Timeout

Edit [template.yaml](template.yaml):

```yaml
Globals:
  Function:
    Timeout: 300      # 5 minutes instead of 2
    MemorySize: 512   # 512 MB instead of 256 MB
```

## Differences from Old Deployment

### Old Way (deploy.sh)

❌ Manual IAM role creation
❌ Manual S3 bucket creation
❌ Manual EventBridge setup
❌ Manual Lambda deployment
❌ Risk of orphaned resources
❌ No easy teardown
❌ Hard to replicate across environments

### New Way (SAM)

✅ One command deployment
✅ All resources in code
✅ Complete teardown with `sam delete`
✅ Multiple environments (dev/staging/prod)
✅ Local testing
✅ Version controlled infrastructure
✅ Repeatable deployments

## Troubleshooting

### "S3 bucket already exists"

S3 bucket names are globally unique. Change the name in [samconfig.toml](samconfig.toml):

```toml
"S3BucketName=river-data-ireland-yourname-prod"
```

### "Access Denied"

Your AWS credentials need these permissions:
- IAM (create roles)
- Lambda (create/update functions)
- S3 (create buckets)
- CloudFormation (create stacks)
- EventBridge (create rules)

### "SAM CLI not found"

Install SAM CLI:
```bash
brew install aws-sam-cli  # macOS
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for other platforms.

## Next Steps

1. **Install SAM CLI**: `brew install aws-sam-cli`
2. **Configure AWS**: `aws configure`
3. **Deploy**: `sam build && sam deploy --guided`
4. **Monitor**: `sam logs --tail`
5. **Teardown**: `sam delete` (when done)

## Resources

- 📖 **Full deployment guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- 🏗️ **Infrastructure definition**: [template.yaml](template.yaml)
- ⚙️ **Configuration**: [samconfig.toml](samconfig.toml)
- 📚 **AWS SAM Documentation**: https://docs.aws.amazon.com/serverless-application-model/

---

**Ready to deploy?** Run: `sam build && sam deploy --guided`

**Questions?** See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.
