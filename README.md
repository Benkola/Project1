# TTSR — Travel Trust & Safety Risk Scorer (v1)

Privacy-first travel risk-scoring API that produces a deterministic **0–100 risk score** and **action** (allow/review/hold) from non-PII signals. Built to demonstrate platform/API product thinking: **OAuth2 Client Credentials**, **idempotency keys**, **HMAC-signed webhooks with retries**, **audit logging**, **SLOs + dashboards**, and **IaC + CI**.

**Live docs / Pages:** https://benkola.github.io/Project1/  
**Repo:** https://github.com/Benkola/Project1  
**Demo (≤3 min):** (add Loom link)

---

## What this demonstrates (CV-ready)
- **API design:** OpenAPI 3.0, REST conventions, versioning (`/v1`), error model, rate-limit headers
- **Reliability:** Idempotency-Key (exactly-once semantics), webhook outbox + retries
- **Security:** OAuth2 Client Credentials (stub), scoped access, KMS-encrypted secrets, least privilege IAM
- **Observability:** structured JSON logs, metrics, tracing (CloudWatch + X-Ray style)
- **Ops:** SLOs, alarms, runbook playbooks
- **Delivery:** Terraform IaC + GitHub Actions CI

---

## Architecture (AWS-first)

API Gateway (REST)
  → Lambda (Python)
  → DynamoDB (`events`, `webhook_outbox`)
  → CloudWatch + X-Ray (logs/metrics/traces)
  → (Optional) EventBridge schedule for webhook retries
  → S3 (artefacts/screenshots)

> Diagram: `docs/architecture.png` (add a diagram screenshot)

---

## API surface (v1)
- `POST /v1/score` — idempotent scoring request (requires `Idempotency-Key`)
- `GET /v1/events/{id}` — fetch event + audit trail
- `POST /v1/webhooks/test` — fire signed webhook test
- `GET /v1/health` — health check

OpenAPI: `api/openapi.yaml`  
Postman collection: `postman/TTSR.postman_collection.json`

---

## Privacy-first contract (important)
- **No PII is accepted or stored.** Signals are numeric/categorical only.
- Schema validation rejects unknown/free-text fields.
- DPIA-lite checklist: `docs/dpia_lite.md`

---

## Scoring model (v0 rules)
Signals (examples):
- `delay` (0..1)
- `weather` (0..1)
- `geo` (0..1)
- `payment_anomaly` (0 or 1)

Output:
- `score` (0..100)
- `action` = `allow` (<30), `review` (30–59), `hold` (≥60)
- `score_version` = `v0_rules`

---

## Idempotency (exactly-once semantics)
`POST /v1/score` requires:
- `Idempotency-Key: <uuid>`

Behaviour:
- Same key + same payload → returns the original result (replay)
- Same key + different payload → **409 conflict**

Implementation notes:
- Idempotency record stored in DynamoDB + request hash comparison
- This prevents duplicate processing during client retries/timeouts

---

## Webhooks (HMAC signing + retry)
Outgoing webhook headers:
- `TTSR-Signature: t=<unix>,v1=<hmac_sha256(timestamp+"."+body)>`

Reliability:
- Writes to `webhook_outbox` first
- Worker retries with exponential backoff until delivered / failed

Code:
- Signing: `webhooks/lib/signer.py`
- Retry worker: `webhooks/worker/worker.py`

---

## SLOs & Observability
SLO targets (demo):
- **Availability:** 99.9% monthly (error budget ~43m)
- **Latency:** p95 ≤ 450ms
- **Errors:** 5xx ≤ 1% rolling

Dashboards/alerts:
- CloudWatch dashboards + alarms (see `docs/slo_dashboard.md`)
- Traces: X-Ray enabled on Lambdas
- Logs: structured JSON with `trace_id` correlation

Runbook:
- `docs/runbook.md` (rollback, incident playbooks, secret rotation)

---

## Quickstart (golden flow)

### 1) Get token (OAuth2 stub)
```bash
export TOKEN=$(curl -s -X POST "$TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=demo-app&client_secret=demo-secret&scope=score:write%20events:read%20webhooks:write" \
  | jq -r .access_token)
