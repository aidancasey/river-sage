# Phase 2: River Guru Web App - Requirements Document

## Project Overview

**River Guru** is a mobile-friendly single-page web application that displays real-time and historical river flow data for the Inniscarra Dam on the River Lee. The application will read data from S3 and provide an intuitive, visual interface for users to monitor river conditions.

## Objectives

1. Create a responsive, mobile-first Vue.js web application
2. Display current flow rate data for Inniscarra Dam
3. Visualize historical flow rate trends with interactive charts
4. Deploy as a static website to AWS S3 with CloudFront CDN
5. Integrate with existing AWS SAM deployment infrastructure
6. Provide fast, reliable access to river data for end users

## Functional Requirements

### FR1: Current Flow Display
- **FR1.1**: Display the most recent flow rate reading
- **FR1.2**: Show the timestamp of the last reading (with timezone)
- **FR1.3**: Display flow rate in cubic meters per second (m³/s)
- **FR1.4**: Show visual indicator (color-coded) for flow levels:
  - Low: < 5 m³/s (blue)
  - Normal: 6-20 m³/s (green)
  - High: 30-60 m³/s (yellow)
  - Very High: > 100 m³/s (red)
- **FR1.5**: Show "data freshness" indicator (e.g., "Updated 5 minutes ago")
- **FR1.6**: Display location information (Inniscarra Dam, River Lee)

### FR2: Historical Flow Visualization
- **FR2.1**: Display line chart showing flow rates over time
- **FR2.2**: Support multiple time ranges:
  - Last 24 hours (default)
  - Last 7 days
  - Last 30 days
  - Last 90 days
- **FR2.3**: Interactive chart features:
  - Hover to see exact values
  - Zoom and pan capabilities
  - Responsive to screen size
- **FR2.4**: Show min/max/average values for selected time range
- **FR2.5**: Display trend indicator (increasing/decreasing/stable)

### FR3: Data Fetching
- **FR3.1**: Fetch latest aggregated data from S3 bucket
- **FR3.2**: Auto-refresh data every 5 minutes
- **FR3.3**: Show loading states while fetching data
- **FR3.4**: Handle errors gracefully with user-friendly messages
- **FR3.5**: Implement data caching to reduce S3 requests
- **FR3.6**: Support offline mode with last cached data

### FR4: User Interface
- **FR4.1**: Mobile-first responsive design
- **FR4.2**: Clean, modern interface following Vue 3 best practices
- **FR4.3**: Dark mode toggle (optional for Phase 2)
- **FR4.4**: Accessible design (WCAG 2.1 Level AA)
- **FR4.5**: Fast initial load time (< 3 seconds)
- **FR4.6**: Smooth animations and transitions

## Non-Functional Requirements

### NFR1: Performance
- **NFR1.1**: Initial page load < 3 seconds on 3G connection
- **NFR1.2**: Time to Interactive (TTI) < 5 seconds
- **NFR1.3**: Lighthouse Performance score > 90
- **NFR1.4**: Optimize bundle size (< 500KB gzipped)

### NFR2: Scalability
- **NFR2.1**: Support 10,000 concurrent users
- **NFR2.2**: CloudFront CDN for global content delivery
- **NFR2.3**: S3 bucket configured for high availability

### NFR3: Security
- **NFR3.1**: HTTPS only (enforced via CloudFront)
- **NFR3.2**: CORS configuration for S3 data access
- **NFR3.3**: No sensitive data exposed in frontend code
- **NFR3.4**: Content Security Policy (CSP) headers

### NFR4: Maintainability
- **NFR4.1**: Well-documented code with JSDoc comments
- **NFR4.2**: Component-based architecture
- **NFR4.3**: Automated testing (unit + integration)
- **NFR4.4**: CI/CD pipeline for automated deployments

### NFR5: Compatibility
- **NFR5.1**: Support modern browsers (Chrome, Firefox, Safari, Edge - last 2 versions)
- **NFR5.2**: Mobile browsers (iOS Safari, Chrome Mobile)
- **NFR5.3**: Screen sizes from 320px to 4K displays

## Technical Architecture

### Frontend Stack
- **Framework**: Vue 3 (Composition API)
- **Build Tool**: Vite
- **UI Library**: TailwindCSS or Bootstrap Vue
- **Charting**: Chart.js or Apache ECharts
- **HTTP Client**: Axios or native Fetch API
- **State Management**: Pinia (if needed)
- **Date Handling**: date-fns or Day.js

### AWS Infrastructure
- **Hosting**: S3 Static Website
- **CDN**: CloudFront
- **API**: API Gateway + Lambda (for data access)
- **Data Storage**: Existing S3 bucket (river-data-ireland-prod)
- **Deployment**: AWS SAM + CloudFormation
- **DNS**: Route 53 (optional)
- **SSL/TLS**: AWS Certificate Manager

### Data Flow
1. Vue app loads from S3/CloudFront
2. App calls API Gateway endpoint (or reads directly from S3)
3. Lambda function (if API Gateway) fetches data from S3
4. Data returned to frontend as JSON
5. Vue app renders current flow and historical chart
6. Auto-refresh every 5 minutes

## Data API Design

### Endpoint 1: Get Latest Flow
```
GET /api/flow/latest
Response:
{
  "stationId": "inniscarra",
  "name": "Inniscarra",
  "river": "River Lee",
  "currentFlow": 85.3,
  "unit": "m³/s",
  "timestamp": "2025-12-06T14:03:00Z",
  "dataAge": 5,
  "status": "normal"
}
```

### Endpoint 2: Get Historical Flow
```
GET /api/flow/history?station=inniscarra&hours=24
Response:
{
  "stationId": "inniscarra",
  "timeRange": {
    "start": "2025-12-05T14:03:00Z",
    "end": "2025-12-06T14:03:00Z"
  },
  "dataPoints": [
    {
      "timestamp": "2025-12-05T14:03:00Z",
      "flow": 82.1
    },
    {
      "timestamp": "2025-12-05T15:03:00Z",
      "flow": 83.5
    }
    // ... more data points
  ],
  "statistics": {
    "min": 78.2,
    "max": 89.7,
    "average": 84.3,
    "trend": "stable"
  }
}
```

## Deployment Architecture

### SAM Template Structure
```
river-data-scraper/
├── template.yaml (updated with web app resources)
├── web-app/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── composables/
│   │   ├── assets/
│   │   └── App.vue
│   ├── public/
│   ├── dist/ (build output)
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
└── api/
    └── data-api.py (Lambda function for data API)
```

### SAM Resources to Add
1. **S3 Bucket** for web hosting (river-guru-web)
2. **CloudFront Distribution**
3. **API Gateway** REST API
4. **Lambda Function** for data API
5. **IAM Roles** for Lambda to read S3 data
6. **CloudWatch Logs** for API monitoring

## UI Wireframes (Text-Based)

### Mobile View (320px - 768px)
```
┌─────────────────────────┐
│   River Guru 🌊         │
│─────────────────────────│
│  Inniscarra Dam         │
│  River Lee              │
│                         │
│  ┌─────────────────┐    │
│  │   85.3 m³/s     │    │
│  │   [NORMAL]      │    │
│  │ Updated 5 min ago│   │
│  └─────────────────┘    │
│                         │
│  [24h][7d][30d][90d]    │
│                         │
│  ┌─────────────────┐    │
│  │                 │    │
│  │  [Line Chart]   │    │
│  │                 │    │
│  └─────────────────┘    │
│                         │
│  Min: 78 | Max: 90      │
│  Avg: 84 | Trend: ↗     │
└─────────────────────────┘
```

### Desktop View (1024px+)
```
┌───────────────────────────────────────────────────┐
│  River Guru 🌊                    [Dark Mode] [?] │
├───────────────────────────────────────────────────┤
│                                                   │
│  Inniscarra Dam - River Lee                      │
│                                                   │
│  ┌──────────────┐  ┌────────────────────────┐    │
│  │              │  │                        │    │
│  │   85.3 m³/s  │  │  [Line Chart - Wider]  │    │
│  │   NORMAL     │  │                        │    │
│  │              │  │                        │    │
│  │ Updated 5m   │  └────────────────────────┘    │
│  └──────────────┘                                │
│                   [24h] [7d] [30d] [90d]         │
│                                                   │
│  Statistics:                                      │
│  Min: 78.2 | Max: 89.7 | Avg: 84.3 | Trend: ↗   │
│                                                   │
└───────────────────────────────────────────────────┘
```

## Success Criteria

### Phase 2 Completion
- [ ] Vue.js app built and tested locally
- [ ] Real-time flow data displayed correctly
- [ ] Historical chart renders with last 24 hours of data
- [ ] Responsive design works on mobile and desktop
- [ ] Deployed to S3 with CloudFront
- [ ] API Gateway + Lambda serving data from S3
- [ ] Integrated with SAM deployment (single command deploy)
- [ ] Lighthouse Performance score > 90
- [ ] Unit test coverage > 80%
- [ ] Documentation complete

### Phase 2.1 (Future Enhancements)
- [ ] Dark mode implementation
- [ ] Multiple stations support
- [ ] Weather data integration
- [ ] Rainfall correlation
- [ ] User preferences (save time range)
- [ ] PWA capabilities (offline support)
- [ ] Push notifications for high flow alerts

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| S3 CORS issues prevent data access | High | Medium | Configure CORS properly; Use API Gateway as proxy |
| Large data files cause slow load times | High | Medium | Implement pagination; Cache data; Use Lambda for aggregation |
| CloudFront costs exceed budget | Medium | Low | Monitor usage; Set billing alarms; Optimize caching |
| Chart library performance on mobile | Medium | Medium | Test early; Use lightweight library; Implement data sampling |
| Browser compatibility issues | Medium | Low | Use Vite's browser targets; Test on all platforms |

## Timeline Estimate

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Setup & Infrastructure** | 2 days | SAM template updates, API Gateway, Lambda function |
| **Frontend Development** | 5 days | Vue app scaffold, components, data fetching, charts |
| **Testing & Optimization** | 2 days | Unit tests, E2E tests, performance optimization |
| **Deployment & Documentation** | 1 day | Deploy to AWS, update docs, verify production |
| **Total** | **10 days** | |

## Budget Estimate (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| S3 (Web Hosting) | 1 GB storage, 10K requests | $0.05 |
| CloudFront | 10 GB data transfer | $1.00 |
| API Gateway | 10K requests | $0.04 |
| Lambda (Data API) | 10K invocations × 1s | $0.00 (free tier) |
| Route 53 (Optional) | 1 hosted zone | $0.50 |
| **Total** | | **~$1.60/month** |

## References

- Vue 3 Documentation: https://vuejs.org/
- Chart.js: https://www.chartjs.org/
- TailwindCSS: https://tailwindcss.com/
- AWS SAM for Static Websites: https://docs.aws.amazon.com/serverless-application-model/
- S3 Static Website Hosting: https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html
