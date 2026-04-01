# Deployment & Architecture Improvements

Identified improvements to make deployments more streamlined and less error-prone.

## 1. ~~Add CI/CD Pipeline~~ DONE

- [x] GitHub Actions workflow (`.github/workflows/deploy.yml`) deploys on push to `main`
- [x] `test` + `validate` jobs run in parallel; `deploy` only runs if both pass
- [x] OIDC federation — IAM role `github-actions-river-sage` with short-lived tokens, no stored keys
- [x] Twilio secrets resolved at Lambda runtime from SSM (not at deploy time)
- [x] Web app `VITE_API_BASE_URL` fetched from CloudFormation outputs during CI build

---

## 2. ~~Wire CloudWatch Alarms to SNS~~ DONE

- [x] SNS topic `${StackName}-alarms` with email subscription
- [x] Email address stored in SSM (`/river-data-scraper/alert-email`), not in source code
- [x] Both error and throttle alarms wired with `AlarmActions` + `OKActions`

---

## 3. ~~Remove Redundant Secret Injection from Makefile~~ DONE

- [x] Removed entire `.env.secrets` / parameter override block from Makefile
- [x] Twilio secrets read from SSM at Lambda runtime (not deploy time)
- [x] Also cleaned up leftover Dash0/OTEL references from Makefile

---

## 4. Externalise Data Source Configuration

**Priority:** Medium | **Effort:** Medium

The 7-station `DATA_SOURCES_JSON` is a large inline JSON blob in `template.yaml`. Adding/removing a station requires a CloudFormation deployment.

**Action items:**
- [ ] Move station config to an S3 object (e.g., `config/data_sources.json`) or SSM parameter
- [ ] Update collector to read config at invocation time
- [ ] Station changes become instant without redeployment

---

## 5. Add S3 Lifecycle Policies

**Priority:** Medium | **Effort:** Low (~20 min)

Raw PDFs and CSVs accumulate indefinitely in S3 with no cleanup.

**Action items:**
- [ ] Add lifecycle rule: transition `raw/` to Glacier after 90 days
- [ ] Add lifecycle rule: expire `raw/` after 1 year
- [ ] Define in CloudFormation or apply directly to the bucket

---

## 6. Stop Committing `web/dist/` to Git

**Priority:** Medium | **Effort:** Low

The built Vue.js output is in the repo, causing merge conflicts and bloating history.

**Action items:**
- [ ] Add `web/dist/` to `.gitignore`
- [ ] Remove `web/dist/` from tracked files (`git rm -r --cached web/dist`)
- [ ] Ensure CI/CD pipeline runs `npm run build` before `deploy-web`

---

## 7. Trim Unnecessary Code from Lambda Packages

**Priority:** Low | **Effort:** Low (~10 min)

Both Makefile build targets copy `src/` **and** `api/` into every artifact. The collector doesn't use `api/`, and the alerts function doesn't need `src/` parsers.

**Action items:**
- [ ] `build-RiverDataCollectorFunction`: only copy `src/`
- [ ] `build-AlertsApiFunction`: only copy `api/`
- [ ] Verify handlers still resolve after the change

---

## 8. Enforce Changeset Review for Production

**Priority:** Low | **Effort:** Low

The Makefile uses `--no-confirm-changeset`, bypassing CloudFormation changeset review even though `samconfig.toml` sets `confirm_changeset = true` for prod.

**Action items:**
- [ ] Remove `--no-confirm-changeset` from the Makefile `deploy-infrastructure` target
- [ ] Let `samconfig.toml` control this per environment (dev=skip, prod=confirm)
