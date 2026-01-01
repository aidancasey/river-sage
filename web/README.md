# River Guru Web App

A mobile-first Vue.js single-page application for visualizing real-time and historical river flow data from Irish rivers.

## Features

- **Real-Time Flow Display**: Current flow rate with color-coded status indicators
- **Interactive Charts**: Historical flow data visualization with multiple time ranges (24h, 7d, 30d, 90d)
- **Hourly Data Collection**: Backend automatically collects data every hour at 30 minutes past
- **Mobile-First Design**: Responsive layout optimized for mobile devices
- **Fast Loading**: Built with Vite for optimal performance

## Tech Stack

- **Framework**: Vue.js 3 with Composition API
- **Build Tool**: Vite
- **Styling**: TailwindCSS 3
- **Charts**: Chart.js with vue-chartjs
- **HTTP Client**: Axios
- **Date Formatting**: date-fns

## Development

### Prerequisites

- Node.js 18+ and npm
- AWS CLI configured with credentials (for deployment)

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Environment Variables

The API endpoint is configured in [.env](.env):

```env
VITE_API_BASE_URL=https://your-api-gateway-url.amazonaws.com/production
```

## Deployment

### Automated Deployment

```bash
# Deploy to production
./deploy.sh production
```

### Manual Deployment

```bash
npm run build
aws s3 sync dist/ s3://river-guru-web-production/ --region eu-west-1 --delete
```

## Production URL

http://river-guru-web-production.s3-website-eu-west-1.amazonaws.com

## TODO / Future Enhancements

- [ ] **Raw File Cleanup**: Implement automatic deletion of raw files (PDFs and CSVs) after they have been processed and stored in parsed format. This will reduce S3 storage costs over time. Consider a retention period (e.g., 30-90 days) before deletion to allow for reprocessing if needed.
- [ ] **Apple Watch API**: Create a lightweight API endpoint that returns the current Inniscarra flow level in a simple format suitable for Apple Watch Shortcuts integration. Should return minimal JSON with just the current flow rate and timestamp for fast loading on watchOS.
- [ ] **Push Notifications**: Implement mobile push notifications for Inniscarra Dam flow level changes. Users can register for alerts during specific time windows (e.g., morning/evening) and receive notifications when flow levels change significantly. Could use AWS SNS for notification delivery and DynamoDB for subscription management.
