.PHONY: help build deploy deploy-dev deploy-staging deploy-prod clean build-web deploy-web test

# Default environment
ENV ?= production

# Colors for output
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)River Data Scraper & River Guru - Unified Deployment$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make deploy-prod    # Deploy everything to production"
	@echo "  make deploy-dev     # Deploy everything to development"
	@echo "  make build          # Build both Lambda and web app"

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf .aws-sam
	rm -rf web/dist
	@echo "$(GREEN)✓ Clean complete$(NC)"

build-web: ## Build Vue.js web application
	@echo "$(BLUE)Building Vue.js web application...$(NC)"
	cd web && npm install && npm run build
	@echo "$(GREEN)✓ Web app build complete$(NC)"

build-lambda: ## Build Lambda functions with SAM
	@echo "$(BLUE)Building Lambda functions with SAM...$(NC)"
	sam build
	@echo "$(GREEN)✓ Lambda build complete$(NC)"

build: build-web build-lambda ## Build everything (web app + Lambda)

deploy-web: ## Deploy web app to S3 (requires ENV to be set)
	@echo "$(BLUE)Deploying web app to S3 ($(ENV))...$(NC)"
	@if [ ! -d "web/dist" ]; then \
		echo "$(YELLOW)Web app not built. Building now...$(NC)"; \
		$(MAKE) build-web; \
	fi
	aws s3 sync web/dist/ s3://river-guru-web-$(ENV)/ \
		--region eu-west-1 \
		--delete \
		--cache-control "max-age=31536000,public"
	@echo "$(GREEN)✓ Web app deployed to river-guru-web-$(ENV)$(NC)"

deploy-infrastructure: ## Deploy infrastructure with SAM (requires ENV to be set)
	@echo "$(BLUE)Deploying infrastructure with SAM ($(ENV))...$(NC)"
	sam deploy --config-env $(ENV) --no-confirm-changeset
	@echo "$(GREEN)✓ Infrastructure deployed$(NC)"

deploy: build deploy-infrastructure deploy-web ## Build and deploy everything
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)Deployment Complete!$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo ""
	@echo "$(BLUE)Retrieving deployment URLs...$(NC)"
	@aws cloudformation describe-stacks \
		--stack-name river-data-scraper-$(ENV) \
		--region eu-west-1 \
		--query 'Stacks[0].Outputs[?OutputKey==`RiverGuruApiUrl` || OutputKey==`RiverGuruWebsiteUrl`].[OutputKey,OutputValue]' \
		--output table || true

deploy-dev: ## Deploy to development environment
	@$(MAKE) deploy ENV=dev

deploy-staging: ## Deploy to staging environment
	@$(MAKE) deploy ENV=staging

deploy-prod: ## Deploy to production environment
	@$(MAKE) deploy ENV=production

test-api: ## Test API endpoints
	@echo "$(BLUE)Testing API endpoints...$(NC)"
	@echo "Testing /latest endpoint:"
	@curl -s "https://3su2ubk6j2.execute-api.eu-west-1.amazonaws.com/production/api/flow/latest" | jq '.currentFlow, .status'
	@echo ""
	@echo "Testing /history endpoint:"
	@curl -s "https://3su2ubk6j2.execute-api.eu-west-1.amazonaws.com/production/api/flow/history?hours=24" | jq '.count, .statistics.trend'

validate: ## Validate SAM template
	@echo "$(BLUE)Validating SAM template...$(NC)"
	sam validate
	@echo "$(GREEN)✓ Template is valid$(NC)"

logs: ## Tail Lambda function logs
	sam logs --tail --stack-name river-data-scraper-$(ENV)

invoke: ## Manually invoke Lambda function
	@echo "$(BLUE)Invoking data collector Lambda...$(NC)"
	aws lambda invoke \
		--function-name river-data-scraper-$(ENV)-collector \
		--region eu-west-1 \
		response.json
	@cat response.json | jq .
	@rm response.json

teardown: ## Delete stack (WARNING: destructive!)
	@echo "$(YELLOW)WARNING: This will delete the entire stack!$(NC)"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	sam delete --stack-name river-data-scraper-$(ENV) --region eu-west-1 --no-prompts

# Development helpers
dev-web: ## Start web app development server
	cd web && npm run dev

dev-lambda: ## Start SAM local API
	sam local start-api

.DEFAULT_GOAL := help
