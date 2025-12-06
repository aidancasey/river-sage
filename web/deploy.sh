#!/bin/bash
#
# Deployment script for River Guru Web App
# Builds and deploys the Vue.js application to S3
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
S3_BUCKET="river-guru-web-${ENVIRONMENT}"
AWS_REGION="eu-west-1"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}River Guru Web App Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "S3 Bucket: ${GREEN}${S3_BUCKET}${NC}"
echo -e "Region: ${GREEN}${AWS_REGION}${NC}"
echo ""

# Step 1: Build the application
echo -e "${BLUE}[1/3] Building application...${NC}"
npm run build

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build completed${NC}"
echo ""

# Step 2: Sync to S3
echo -e "${BLUE}[2/3] Deploying to S3...${NC}"
aws s3 sync dist/ s3://${S3_BUCKET}/ \
    --region ${AWS_REGION} \
    --delete \
    --cache-control "max-age=31536000,public"

if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Deployment completed${NC}"
echo ""

# Step 3: Get website URL
echo -e "${BLUE}[3/3] Retrieving website URL...${NC}"
WEBSITE_URL=$(aws cloudformation describe-stacks \
    --stack-name "river-data-scraper-${ENVIRONMENT}" \
    --region ${AWS_REGION} \
    --query "Stacks[0].Outputs[?OutputKey=='RiverGuruWebsiteUrl'].OutputValue" \
    --output text 2>/dev/null)

if [ -n "$WEBSITE_URL" ]; then
    echo -e "${GREEN}✓ Website URL: ${WEBSITE_URL}${NC}"
else
    echo -e "${GREEN}✓ Website URL: http://${S3_BUCKET}.s3-website-${AWS_REGION}.amazonaws.com${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment successful!${NC}"
echo -e "${GREEN}========================================${NC}"
