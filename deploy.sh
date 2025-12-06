#!/bin/bash
#
# Unified deployment script for River Data Scraper & River Guru Web App
# This is a wrapper around the Makefile for easier deployment
#

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default to production
ENVIRONMENT=${1:-production}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|development|staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
    echo -e "Valid environments: dev, development, staging, production"
    exit 1
fi

# Normalize environment name
case "$ENVIRONMENT" in
    dev|development)
        ENVIRONMENT="dev"
        ;;
    staging)
        ENVIRONMENT="staging"
        ;;
    production)
        ENVIRONMENT="production"
        ;;
esac

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}River Data Scraper & River Guru${NC}"
echo -e "${BLUE}Unified Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo ""

# Check if make is available
if ! command -v make &> /dev/null; then
    echo -e "${RED}Error: 'make' command not found${NC}"
    echo -e "Please install make or run deployment commands manually"
    exit 1
fi

# Run deployment via Makefile
echo -e "${BLUE}Starting deployment...${NC}"
echo ""

if [ "$ENVIRONMENT" = "dev" ]; then
    make deploy-dev
elif [ "$ENVIRONMENT" = "staging" ]; then
    make deploy-staging
else
    make deploy-prod
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
