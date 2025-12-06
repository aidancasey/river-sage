# Product Requirements Document: Irish Rivers Data Aggregation System

## 1. Product Overview

### 1.1 Purpose
A low-cost, serverless system to aggregate and serve data about Irish rivers, including water levels, flow rates, and weather conditions. The system will provide historical and current data for analysis and monitoring.

### 1.2 Target Users
- Environmental researchers
- Water sports enthusiasts (kayakers, rowers)
- Local authorities and flood monitoring services
- General public interested in river conditions

### 1.3 Success Metrics
- Data collection reliability: >99% successful hourly data captures
- Operating costs: <$5/month for MVP
- Data freshness: <1 hour lag from source
- API response time: <500ms for typical queries

## 2. System Architecture

### 2.1 AWS Services (Cost-Optimized)

| Service | Purpose | Cost Consideration |
|---------|---------|-------------------|
| AWS Lambda | Serverless data collection | Free tier: 1M requests/month, 400,000 GB-seconds |
| EventBridge | Scheduling (hourly triggers) | Free tier: All state change events |
| S3 | Data storage | Standard tier, ~$0.023/GB/month |
| CloudWatch Logs | Logging and monitoring | 5GB free tier/month |
| API Gateway (Optional) | REST API for data access | Pay-per-request pricing |

### 2.2 Data Flow Architecture

```
┌─────────────────┐
│  EventBridge    │  (Hourly trigger)
│   Scheduler     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda         │
│  PDF Scraper    │──────┐
└────────┬────────┘      │ (on error)
         │               ▼
         │        ┌──────────────┐
         │        │  CloudWatch  │
         │        │  Logs/Alerts │
         │        └──────────────┘
         ▼
┌─────────────────┐
│      S3         │
│  Data Storage   │
│  - Raw PDFs     │
│  - Parsed JSON  │
│  - Aggregated   │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  API Gateway    │  (Future: User access)
│  (Optional)     │
└─────────────────┘
```

## 3. Component 1: River Flow Data Collector

### 3.1 Functional Requirements

#### FR1: Data Source Connection
- **Source**: ESB Hydro - Inniscarra Flow PDF
- **URL**: `http://www.esbhydro.ie/Lee/04-Inniscarra-Flow.pdf`
- **Frequency**: Every hour (24 executions/day)
- **Retry Logic**: 3 retry attempts with exponential backoff on failure

#### FR2: PDF Data Extraction
- Download PDF document
- Extract the following data points:
  - Current flow rate (m³/s)
  - Timestamp of measurement
  - Average flow rate (if available)
  - Any status indicators (normal, high, low)
- Handle PDF format variations gracefully

#### FR3: Data Storage
- **S3 Bucket Structure**:
  ```
  river-data-ireland/
  ├── raw/
  │   └── inniscarra/
  │       └── YYYY/MM/DD/
  │           └── inniscarra_flow_YYYYMMDD_HHMMSS.pdf
  ├── parsed/
  │   └── inniscarra/
  │       └── YYYY/MM/
  │           └── inniscarra_flow_YYYYMM.json
  └── aggregated/
      └── inniscarra_latest.json
      └── inniscarra_daily_averages.json
  ```

- **Data Format** (JSON):
  ```json
  {
    "river": "River Lee",
    "station": "Inniscarra",
    "timestamp": "2025-12-01T14:00:00Z",
    "collected_at": "2025-12-01T14:05:23Z",
    "flow_rate_m3s": 45.2,
    "status": "normal",
    "source_url": "http://www.esbhydro.ie/Lee/04-Inniscarra-Flow.pdf",
    "metadata": {
      "scraper_version": "1.0.0",
      "pdf_hash": "abc123..."
    }
  }
  ```

#### FR4: Error Handling
- Log all errors to CloudWatch
- Send SNS notification for consecutive failures (>3)
- Store failed PDFs for manual inspection
- Continue operation even if parsing fails

### 3.2 Non-Functional Requirements

#### NFR1: Cost Optimization
- Lambda memory: 256MB (sufficient for PDF processing)
- Lambda timeout: 60 seconds
- Use S3 Intelligent-Tiering for automatic cost optimization
- Compress JSON data with gzip
- Archive raw PDFs to S3 Glacier after 30 days

#### NFR2: Reliability
- Idempotent operations (safe to retry)
- Deduplication based on timestamp
- Health check endpoint

#### NFR3: Scalability
- Design to support multiple rivers/stations
- Configuration-driven station management
- Extensible to add weather data sources

#### NFR4: Monitoring
- CloudWatch metrics:
  - Successful scrapes/hour
  - Failed scrapes/hour
  - Lambda execution duration
  - S3 storage size
- CloudWatch alarms for:
  - Lambda errors >3 in 1 hour
  - No successful execution in 2 hours

## 4. Technical Implementation

### 4.1 Technology Choice: **Python**

**Rationale**:
- Excellent PDF parsing libraries (pdfplumber, PyPDF2, tabula-py)
- Strong AWS SDK (boto3)
- Efficient for text processing and data manipulation
- Well-suited for Lambda environment

### 4.2 Python Dependencies
```
pdfplumber>=0.10.0
boto3>=1.28.0
requests>=2.31.0
python-dateutil>=2.8.0
```

### 4.3 Lambda Function Structure
```python
# handler.py
def lambda_handler(event, context):
    1. Download PDF from source URL
    2. Extract flow data using pdfplumber
    3. Validate and structure data
    4. Upload raw PDF to S3
    5. Upload parsed JSON to S3
    6. Update latest/aggregated files
    7. Return success/failure status
```

### 4.4 Configuration Management
```json
{
  "stations": [
    {
      "id": "inniscarra",
      "name": "Inniscarra",
      "river": "River Lee",
      "url": "http://www.esbhydro.ie/Lee/04-Inniscarra-Flow.pdf",
      "type": "pdf",
      "parser": "esb_hydro_flow",
      "enabled": true
    }
  ],
  "s3": {
    "bucket": "river-data-ireland",
    "region": "eu-west-1"
  },
  "schedule": "rate(1 hour)"
}
```

## 5. Future Enhancements (Post-MVP)

### 5.1 Phase 2: Additional Data Sources
- Multiple river stations
- Weather data integration (Met Éireann API)
- Rainfall data
- Water quality metrics

### 5.2 Phase 3: User Interface
- Static website hosted on S3 + CloudFront
- Interactive charts (Chart.js)
- Historical data visualization
- Alerts/notifications for threshold breaches

### 5.3 Phase 4: Advanced Features
- Predictive analytics (flood risk)
- Mobile app
- User accounts and saved preferences
- Data export functionality

## 6. Implementation Timeline

### Week 1: MVP Development
- [ ] Set up AWS infrastructure (S3, Lambda, EventBridge)
- [ ] Develop PDF scraper Lambda function
- [ ] Implement S3 storage logic
- [ ] Add error handling and logging

### Week 2: Testing & Monitoring
- [ ] Test with various PDF formats
- [ ] Set up CloudWatch dashboards
- [ ] Configure alarms and notifications
- [ ] Load testing and optimization

### Week 3: Documentation & Launch
- [ ] Technical documentation
- [ ] Deployment automation (Infrastructure as Code)
- [ ] Monitor for 7 days
- [ ] Gather feedback and iterate

## 7. Cost Estimation

### Monthly Operating Costs (MVP)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 720 invocations/month × 30s × 256MB | $0.00 (Free tier) |
| EventBridge | 720 events/month | $0.00 (Free tier) |
| S3 Storage | ~500MB/month | $0.01 |
| S3 Requests | ~1,500 PUT/GET | $0.01 |
| CloudWatch Logs | ~100MB/month | $0.00 (Free tier) |
| **Total** | | **~$0.02/month** |

### Scaling Costs (10 stations, 1 year of data)
- S3 Storage: ~6GB = $0.14/month
- Lambda: Still within free tier
- **Total**: ~$0.15/month

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| PDF format changes | High | Implement multiple parsing strategies, alerts on failures |
| Source URL becomes unavailable | High | Monitor uptime, implement fallback sources |
| Data quality issues | Medium | Validation rules, manual review workflow |
| AWS costs exceed budget | Low | Set up billing alarms, use free tier effectively |

## 9. Success Criteria

- ✅ System collects data successfully 23/24 hours per day (95%+ reliability)
- ✅ Operating costs remain under $5/month
- ✅ Data is accessible and queryable from S3
- ✅ System requires <2 hours/month maintenance
- ✅ Architecture supports adding 5+ additional data sources with minimal changes

## 10. Appendix

### 10.1 AWS Region Selection
**Recommended**: `eu-west-1` (Ireland)
- Closest to data source
- GDPR compliance
- Low latency

### 10.2 Security Considerations
- S3 bucket: Private (no public access)
- Lambda: Minimal IAM permissions (S3 read/write only)
- Secrets: Store API keys in AWS Secrets Manager or SSM Parameter Store
- Encryption: S3 server-side encryption enabled

### 10.3 Data Retention Policy
- Raw PDFs: 30 days hot storage → Glacier
- Parsed JSON: Retain indefinitely (low cost)
- Logs: 7 days retention in CloudWatch
