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

## 4. ~~Externalise Data Source Configuration~~ DONE

- [x] Moved to `config/data_sources.json` in the repo
- [x] Lambda reads from `s3://river-data-ireland-prod/config/data_sources.json` at startup
- [x] CI uploads the file to S3 on every deploy
- [x] Station changes take effect on next Lambda invocation — no CloudFormation deploy needed

---

## 5. ~~Add S3 Lifecycle Policies~~ DONE

- [x] `raw/` transitions to Glacier after 90 days, expires after 365 days
- [x] `parsed/` transitions to Intelligent-Tiering after 30 days (pre-existing)
- [x] Noncurrent versions expire after 90 days (pre-existing)
- Applied directly to `river-data-ireland-prod` bucket (bucket lives outside CloudFormation)

---

## 6. ~~Stop Committing `web/dist/` to Git~~ DONE

- [x] `web/dist/` already in `.gitignore` — was never tracked
- [x] CI builds the web app fresh on every deploy

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
