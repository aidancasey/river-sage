# Deployment & Architecture Improvements

Identified improvements to make deployments more streamlined and less error-prone.

## 1. Add CI/CD Pipeline

**Priority:** High | **Effort:** Medium

Deployments are fully manual (`make deploy-prod` from a local machine). No automated tests run before deploy, secrets must exist locally, and there's no audit trail.

**Decisions made:**
- Deploy to production on merge/push to `main` (no staging environment)
- Use OIDC federation instead of long-lived AWS access keys (short-lived tokens, nothing to rotate or leak)
- Twilio secrets stay in SSM Parameter Store — no need to duplicate them in GitHub

**Implemented:**
- [x] GitHub Actions workflow: `.github/workflows/deploy.yml`
  - `test` job — runs `pytest` on every push to `main`
  - `validate` job — runs `sam validate --lint` in parallel
  - `deploy` job — builds and deploys Lambda + web app (only if test + validate pass)

**Remaining — AWS OIDC setup (one-time):**
- [ ] Create IAM OIDC identity provider in AWS for `token.actions.githubusercontent.com`
- [ ] Create IAM role with trust policy scoped to `aidancasey/river-sage:ref:refs/heads/main`
- [ ] Grant the role permissions: S3, CloudFormation, Lambda, IAM, API Gateway, EventBridge, CloudWatch, SSM read
- [ ] Update workflow to use `role-to-assume` instead of access key secrets
- [ ] Create `production` environment in GitHub repo settings (optional — adds approval gate)

**Remaining — switch workflow to OIDC auth:**
- [ ] Replace `aws-access-key-id` / `aws-secret-access-key` with `role-to-assume: arn:aws:iam::ACCOUNT_ID:role/github-actions-river-sage`
- [ ] Remove `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from GitHub secrets (if added)

---

## 2. Wire CloudWatch Alarms to SNS

**Priority:** High | **Effort:** Low (~30 min)

`template.yaml` defines error and throttle alarms but they have **no `AlarmActions`** — Lambda failures are currently silent.

**Action items:**
- [ ] Add an SNS topic resource to `template.yaml`
- [ ] Add email/Slack subscription to the topic
- [ ] Wire `AlarmActions` on both existing alarms to the SNS topic

---

## 3. Remove Redundant Secret Injection from Makefile

**Priority:** High | **Effort:** Low (~15 min)

The Makefile `deploy-infrastructure` target reads `.env.secrets` and passes Twilio values as `--parameter-overrides`, but Twilio secrets are already resolved from SSM Parameter Store by CloudFormation. The override path is a leftover that could conflict.

**Action items:**
- [ ] Remove Twilio credential handling from `.env.secrets` flow in `Makefile`
- [ ] Confirm `template.yaml` SSM `{{resolve:ssm-secure:...}}` references are the sole source
- [ ] Update `.env.secrets.example` to remove Twilio entries

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
