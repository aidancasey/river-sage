# Phase 2: River Guru Web App - Task List

## Epic 1: Infrastructure & Backend Setup (AWS SAM)

### Task 1.1: Create Data API Lambda Function
- [ ] Create `api/` directory in project root
- [ ] Create `data-api.py` Lambda function
- [ ] Implement `/latest` endpoint handler
  - [ ] Read latest aggregated JSON from S3
  - [ ] Parse and format response
  - [ ] Add error handling
- [ ] Implement `/history` endpoint handler
  - [ ] Read historical data from S3 (by time range)
  - [ ] Calculate statistics (min, max, avg, trend)
  - [ ] Support query parameters (hours, days)
- [ ] Add CORS headers to responses
- [ ] Write unit tests for Lambda function
- [ ] Create `requirements.txt` for Lambda dependencies

**Acceptance Criteria**:
- Lambda function returns valid JSON responses
- Both endpoints tested and working locally
- CORS headers correctly configured
- Error handling returns appropriate HTTP status codes

---

### Task 1.2: Update SAM Template for Web App
- [ ] Add S3 bucket resource for web hosting (`RiverGuruWebBucket`)
  - [ ] Configure as static website
  - [ ] Set public read policy
  - [ ] Add bucket policy for CloudFront
- [ ] Add CloudFront distribution resource
  - [ ] Set S3 bucket as origin
  - [ ] Configure default root object (index.html)
  - [ ] Set up HTTPS (use default CloudFront certificate)
  - [ ] Add custom error pages
- [ ] Add API Gateway REST API resource
  - [ ] Create `/api` resource
  - [ ] Configure CORS
  - [ ] Set up stages (dev, prod)
- [ ] Add Data API Lambda function resource
  - [ ] Configure environment variables (S3_BUCKET_NAME)
  - [ ] Grant S3 read permissions
  - [ ] Connect to API Gateway
- [ ] Add Lambda permissions for API Gateway
- [ ] Update outputs with new resource URLs

**Acceptance Criteria**:
- SAM template validates successfully
- All new resources defined correctly
- Proper IAM permissions configured
- Outputs include CloudFront URL and API Gateway endpoint

---

### Task 1.3: Configure S3 CORS for Data Access
- [ ] Update data bucket CORS configuration
- [ ] Allow GET requests from web app domain
- [ ] Test CORS with browser dev tools

**Acceptance Criteria**:
- Web app can fetch data from S3 without CORS errors
- OPTIONS preflight requests handled correctly

---

### Task 1.4: Deploy Infrastructure to AWS
- [ ] Validate SAM template: `sam validate`
- [ ] Build: `sam build`
- [ ] Deploy to dev environment: `sam deploy --config-env dev`
- [ ] Test API Gateway endpoints
- [ ] Verify CloudFront distribution is active
- [ ] Deploy to production: `sam deploy --config-env production`
- [ ] Document API endpoints in README

**Acceptance Criteria**:
- All infrastructure deployed successfully
- API Gateway endpoints return test data
- CloudFront distribution is accessible
- No errors in CloudWatch Logs

---

## Epic 2: Vue.js Web App Development

### Task 2.1: Initialize Vue.js Project
- [ ] Create `web-app/` directory
- [ ] Initialize Vue 3 project with Vite: `npm create vue@latest`
  - [ ] Select TypeScript: No (or Yes if preferred)
  - [ ] Select Router: Yes
  - [ ] Select Pinia: Yes (for state management)
  - [ ] Select Vitest: Yes (for testing)
  - [ ] Select ESLint: Yes
  - [ ] Select Prettier: Yes
- [ ] Install TailwindCSS: `npm install -D tailwindcss postcss autoprefixer`
- [ ] Configure Tailwind
- [ ] Install Chart.js: `npm install chart.js vue-chartjs`
- [ ] Install Axios: `npm install axios`
- [ ] Install date-fns: `npm install date-fns`
- [ ] Set up `.env` files for API endpoints
- [ ] Configure Vite for production builds
- [ ] Update `package.json` with build script

**Acceptance Criteria**:
- Vue app runs locally: `npm run dev`
- TailwindCSS styling works
- All dependencies installed correctly
- Dev server accessible on localhost

---

### Task 2.2: Create Project Structure & Components
- [ ] Create directory structure:
  ```
  src/
  ├── components/
  │   ├── CurrentFlow.vue
  │   ├── FlowChart.vue
  │   ├── TimeRangeSelector.vue
  │   ├── StationInfo.vue
  │   └── LoadingSpinner.vue
  ├── composables/
  │   ├── useFlowData.js
  │   └── useAutoRefresh.js
  ├── services/
  │   └── api.js
  ├── utils/
  │   ├── formatters.js
  │   └── flowStatus.js
  ├── views/
  │   └── Dashboard.vue
  └── App.vue
  ```
- [ ] Create base layout in `App.vue`
- [ ] Set up routing in `router/index.js`

**Acceptance Criteria**:
- All files and directories created
- Components scaffold in place
- App structure follows Vue 3 best practices

---

### Task 2.3: Implement API Service Layer
- [ ] Create `services/api.js`
- [ ] Implement `getLatestFlow()` function
- [ ] Implement `getHistoricalFlow(hours)` function
- [ ] Add error handling and retry logic
- [ ] Add request caching with localStorage
- [ ] Configure base URL from environment variables
- [ ] Write unit tests for API service

**Acceptance Criteria**:
- API service can fetch data from backend
- Error handling works correctly
- Data cached in localStorage
- Tests pass with 100% coverage

---

### Task 2.4: Create CurrentFlow Component
- [ ] Build `CurrentFlow.vue` component
- [ ] Display current flow rate (large, prominent)
- [ ] Show timestamp of last reading
- [ ] Add flow status indicator (color-coded badge)
- [ ] Display "data age" (e.g., "Updated 5 minutes ago")
- [ ] Add loading state
- [ ] Add error state with retry button
- [ ] Make responsive for mobile and desktop
- [ ] Write component tests

**Acceptance Criteria**:
- Component displays real data from API
- Color-coded status works correctly
- Responsive on all screen sizes
- Loading and error states handled
- Tests pass

---

### Task 2.5: Create FlowChart Component
- [ ] Build `FlowChart.vue` component with Chart.js
- [ ] Configure line chart for flow data
- [ ] Implement time axis (X) and flow rate axis (Y)
- [ ] Add hover tooltips with exact values
- [ ] Make chart responsive to container size
- [ ] Add loading state (skeleton or spinner)
- [ ] Configure chart colors and styling
- [ ] Add zoom and pan interactions (optional)
- [ ] Write component tests

**Acceptance Criteria**:
- Chart renders historical data correctly
- Interactive tooltips work
- Responsive on all devices
- Chart updates when data changes
- Tests pass

---

### Task 2.6: Create TimeRangeSelector Component
- [ ] Build `TimeRangeSelector.vue` component
- [ ] Add buttons for: 24h, 7d, 30d, 90d
- [ ] Highlight active time range
- [ ] Emit event when selection changes
- [ ] Style for mobile (stacked) and desktop (inline)
- [ ] Write component tests

**Acceptance Criteria**:
- Time range selection works
- Active state visually clear
- Emits correct events
- Responsive design
- Tests pass

---

### Task 2.7: Create StationInfo Component
- [ ] Build `StationInfo.vue` component
- [ ] Display station name (Inniscarra Dam)
- [ ] Display river name (River Lee)
- [ ] Add location icon
- [ ] Style consistently with app theme
- [ ] Write component tests

**Acceptance Criteria**:
- Station info displays correctly
- Consistent styling
- Tests pass

---

### Task 2.8: Create Dashboard View
- [ ] Build `Dashboard.vue` view
- [ ] Compose all components together
- [ ] Implement layout (mobile-first)
- [ ] Add statistics section (min, max, avg, trend)
- [ ] Fetch data on mount
- [ ] Handle time range changes
- [ ] Implement auto-refresh (every 5 minutes)
- [ ] Add manual refresh button
- [ ] Write integration tests

**Acceptance Criteria**:
- Dashboard displays all components
- Data flows correctly between components
- Auto-refresh works
- Layout is responsive
- Tests pass

---

### Task 2.9: Implement Composables
- [ ] Create `useFlowData.js` composable
  - [ ] Manage flow data state
  - [ ] Handle API calls
  - [ ] Implement caching logic
  - [ ] Calculate statistics
- [ ] Create `useAutoRefresh.js` composable
  - [ ] Set up 5-minute interval
  - [ ] Clean up on unmount
  - [ ] Pause when tab not visible
- [ ] Write tests for composables

**Acceptance Criteria**:
- Composables work correctly
- State management is clean
- Auto-refresh pauses when inactive
- Tests pass

---

### Task 2.10: Implement Utility Functions
- [ ] Create `formatters.js`
  - [ ] `formatFlowRate(value)` - format number with unit
  - [ ] `formatTimestamp(date)` - human-readable time
  - [ ] `formatDataAge(timestamp)` - "5 minutes ago"
- [ ] Create `flowStatus.js`
  - [ ] `getFlowStatus(value)` - return status (low, normal, high, very high)
  - [ ] `getStatusColor(status)` - return color class
- [ ] Write unit tests for all utilities

**Acceptance Criteria**:
- All formatting functions work correctly
- Flow status logic accurate
- Tests pass with 100% coverage

---

### Task 2.11: Add Loading & Error States
- [ ] Create `LoadingSpinner.vue` component
- [ ] Create error message component
- [ ] Implement loading states in all data-dependent components
- [ ] Add error boundaries
- [ ] Show friendly error messages
- [ ] Add retry functionality

**Acceptance Criteria**:
- Loading states display during data fetch
- Error states show user-friendly messages
- Retry button works
- No blank screens or crashes

---

### Task 2.12: Implement Responsive Design
- [ ] Test on mobile devices (320px, 375px, 414px)
- [ ] Test on tablets (768px, 1024px)
- [ ] Test on desktop (1280px, 1920px)
- [ ] Adjust component layouts for each breakpoint
- [ ] Ensure touch targets are at least 44px × 44px
- [ ] Test in Chrome DevTools device emulator
- [ ] Test on real devices (iOS, Android)

**Acceptance Criteria**:
- App works on all screen sizes
- No horizontal scrolling
- Touch targets appropriate size
- Charts readable on mobile

---

### Task 2.13: Optimize Performance
- [ ] Implement code splitting with lazy loading
- [ ] Optimize images and assets
- [ ] Minimize bundle size
- [ ] Implement service worker for caching (optional)
- [ ] Add meta tags for SEO
- [ ] Run Lighthouse audit
- [ ] Optimize Chart.js rendering
- [ ] Implement debouncing for window resize

**Acceptance Criteria**:
- Lighthouse Performance score > 90
- Bundle size < 500KB gzipped
- Initial load < 3 seconds
- Smooth interactions (60fps)

---

## Epic 3: Testing & Quality Assurance

### Task 3.1: Write Unit Tests
- [ ] Test all components (>80% coverage)
- [ ] Test composables
- [ ] Test utility functions
- [ ] Test API service
- [ ] Run tests: `npm run test:unit`
- [ ] Ensure all tests pass

**Acceptance Criteria**:
- Test coverage > 80%
- All tests pass
- No console errors during tests

---

### Task 3.2: Write Integration Tests
- [ ] Test Dashboard view with mocked API
- [ ] Test data flow between components
- [ ] Test user interactions (clicks, time range changes)
- [ ] Test auto-refresh functionality

**Acceptance Criteria**:
- Integration tests pass
- User flows work correctly
- No regressions detected

---

### Task 3.3: Cross-Browser Testing
- [ ] Test on Chrome (latest)
- [ ] Test on Firefox (latest)
- [ ] Test on Safari (latest)
- [ ] Test on Edge (latest)
- [ ] Test on iOS Safari
- [ ] Test on Chrome Mobile (Android)
- [ ] Document any browser-specific issues

**Acceptance Criteria**:
- App works on all target browsers
- No visual or functional bugs
- Graceful degradation where needed

---

### Task 3.4: Accessibility Testing
- [ ] Run Lighthouse accessibility audit
- [ ] Test keyboard navigation
- [ ] Test with screen reader (VoiceOver or NVDA)
- [ ] Ensure proper ARIA labels
- [ ] Check color contrast ratios
- [ ] Add alt text to images
- [ ] Ensure focus indicators visible

**Acceptance Criteria**:
- Lighthouse Accessibility score > 90
- Keyboard navigation works
- Screen reader compatible
- WCAG 2.1 Level AA compliant

---

## Epic 4: Deployment & DevOps

### Task 4.1: Create Build Script for Web App
- [ ] Add build script to `package.json`: `"build": "vite build"`
- [ ] Configure output directory: `dist/`
- [ ] Add script to copy `dist/` to SAM build folder
- [ ] Test local build: `npm run build`
- [ ] Verify build output is optimized

**Acceptance Criteria**:
- Build script runs successfully
- Output directory contains optimized files
- All assets properly bundled

---

### Task 4.2: Update SAM Build Process
- [ ] Add build hook in `template.yaml` or use Makefile
- [ ] Install Node.js dependencies during SAM build
- [ ] Run Vue build as part of SAM build
- [ ] Copy `dist/` contents to Lambda layer or S3 sync
- [ ] Test: `sam build`

**Acceptance Criteria**:
- `sam build` builds both Lambda and Vue app
- Web app assets ready for deployment
- No build errors

---

### Task 4.3: Deploy Web App to S3
- [ ] Configure SAM to sync `web-app/dist/` to S3 bucket
- [ ] Set correct content types for all files
- [ ] Enable gzip compression
- [ ] Set cache headers for static assets
- [ ] Deploy: `sam deploy --config-env production`
- [ ] Verify files uploaded to S3

**Acceptance Criteria**:
- All web app files in S3 bucket
- Correct content types set
- Gzip compression enabled
- Deployment successful

---

### Task 4.4: Configure CloudFront Invalidation
- [ ] Add CloudFront invalidation to deployment script
- [ ] Invalidate all paths (`/*`) after deployment
- [ ] Test cache clearing works
- [ ] Document invalidation process

**Acceptance Criteria**:
- CloudFront cache invalidates on deploy
- Updated files served immediately
- No stale content after deployment

---

### Task 4.5: Test Production Deployment
- [ ] Access app via CloudFront URL
- [ ] Verify API endpoints work from production app
- [ ] Test all functionality in production
- [ ] Check CloudWatch Logs for errors
- [ ] Monitor API Gateway metrics
- [ ] Test on multiple devices and networks

**Acceptance Criteria**:
- Production app fully functional
- No errors in logs
- Performance meets requirements
- All features working

---

### Task 4.6: Set Up Custom Domain (Optional)
- [ ] Register domain or use existing
- [ ] Configure Route 53 hosted zone
- [ ] Request ACM certificate for domain
- [ ] Update CloudFront distribution with custom domain
- [ ] Add DNS records pointing to CloudFront
- [ ] Test custom domain access

**Acceptance Criteria**:
- Custom domain resolves to CloudFront
- HTTPS works correctly
- No certificate warnings

---

## Epic 5: Documentation & Finalization

### Task 5.1: Update Project README
- [ ] Add "River Guru Web App" section
- [ ] Document Vue.js development workflow
- [ ] Add build and deployment instructions
- [ ] Include screenshots or GIFs
- [ ] Document API endpoints
- [ ] Add troubleshooting section
- [ ] Update architecture diagram

**Acceptance Criteria**:
- README is comprehensive and clear
- New developers can set up project
- All commands documented

---

### Task 5.2: Create Web App README
- [ ] Create `web-app/README.md`
- [ ] Document component structure
- [ ] Explain state management
- [ ] Document API integration
- [ ] Add contribution guidelines
- [ ] Document testing approach

**Acceptance Criteria**:
- Web app has its own detailed README
- Architecture clearly explained
- Development workflow documented

---

### Task 5.3: Update DEPLOYMENT.md
- [ ] Add web app deployment instructions
- [ ] Document CloudFront setup
- [ ] Document API Gateway configuration
- [ ] Add rollback procedures
- [ ] Document monitoring and logging

**Acceptance Criteria**:
- Deployment guide includes web app
- Clear step-by-step instructions
- Troubleshooting tips included

---

### Task 5.4: Create User Guide
- [ ] Create `USER_GUIDE.md`
- [ ] Explain how to use River Guru app
- [ ] Document all features
- [ ] Add FAQ section
- [ ] Include screenshots

**Acceptance Criteria**:
- User guide is clear and helpful
- All features explained
- FAQs answer common questions

---

### Task 5.5: Final Phase 2 Review
- [ ] Code review entire web app
- [ ] Review all documentation
- [ ] Verify all tasks completed
- [ ] Check Phase 2 requirements met
- [ ] Update project roadmap
- [ ] Tag release in Git (v2.0.0)
- [ ] Celebrate! 🎉

**Acceptance Criteria**:
- All tasks completed
- Code quality is high
- Documentation is complete
- Phase 2 successfully delivered

---

## Summary

**Total Tasks**: 52
**Estimated Duration**: 10 days
**Prerequisites**: Phase 1 (Data Scraper) must be complete

### Task Breakdown by Epic
- **Epic 1** (Infrastructure): 4 tasks
- **Epic 2** (Frontend Dev): 13 tasks
- **Epic 3** (Testing & QA): 4 tasks
- **Epic 4** (Deployment): 6 tasks
- **Epic 5** (Documentation): 5 tasks

### Dependencies
- Task 2.1 depends on Task 1.4 (API endpoints must exist)
- Task 4.3 depends on Task 4.2 (build must work)
- Task 4.5 depends on Task 4.3 (deployment must complete)
- All Epic 3 tasks depend on Epic 2 completion

### Next Steps
1. Review requirements and task list
2. Set up development environment
3. Begin with Epic 1 (Infrastructure setup)
4. Follow task list sequentially
5. Update task list as you progress
