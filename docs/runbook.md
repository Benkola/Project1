# TTSR Runbook (v1)

## Service summary
- API: API Gateway (REST) → Lambda (Python) → DynamoDB (events table).
- Auth: OAuth2 Client Credentials (Lambda token stub) + Lambda Authorizer (scope-based).
- Infra: Terraform. Observability: CloudWatch Logs, X-Ray, Dashboard + Alarms.

## Environments
- dev: single region (eu-west-2), single stage `dev`.

## Deploy
1. Local: `cd infra && terraform plan -out=tfplan && terraform apply tfplan`
2. CI (optional): GitHub Actions `deploy` workflow (with AWS creds in repo secrets).

## Rollback
- If last apply introduced errors, re-apply previous plan artifact (if saved) or:
  - `git checkout <previous-tag>` → `terraform plan/apply` to recreate last known-good infra.
- For Lambda-only regressions: upload previous zip via Console or re-apply Terraform with previous commit.

## Secrets
- Auth signing secret: env `AUTH_SIGNING_SECRET` on authorizer & token lambdas.
- Webhook: `WEBHOOK_URL`, `WEBHOOK_SECRET` on score lambda.
- Rotation: update env var → “Deploy new version” in Lambda → test health & score → tag release.

## Incident response
- SEV-1: API down (5xx ≥5% 10m / health fails). Page immediately.
- SEV-2: Elevated latency (p95 > 600ms 10m), or errors >2% 10m. Investigate in next 2h.
- SEV-3: Non-customer-impacting alarms or single-region blips. Triage in business hours.

## Triage checklist
- **Health:** `GET /v1/health` = 200?
- **Logs:** CloudWatch → `/aws/lambda/ttsr-dev-*` filter `ERROR` or recent RequestId.
- **Traces:** X-Ray Service map → investigate cold starts, retries, downstream (Dynamo).
- **API metrics:** API Gateway 5XXError, Latency (p95), Count—by stage `dev`.
- **Lambda metrics:** Errors, Throttles, Duration (p95).
- **DynamoDB:** ThrottledRequests, ConditionalCheckFailed (idempotency).

## Playbooks
### A. 5xx spike
1. CloudWatch Logs for gateway-integrated Lambda; look for python stack traces.
2. If “Decimal not JSON serializable” → ensure `get_event.py` converts `Decimal` → numbers.
3. If ImportError → ensure handler is self-contained; redeploy zip (Terraform).

### B. Latency p95 > 600ms
- Check cold starts (Init Duration) → increase memory (faster CPU) from 128 → 256/512.
- Add provisioned concurrency (later) if consistently cold.
- Dynamo slow? Look at `ConsumedRead/WriteCapacity` (we use on-demand).

### C. Auth 403s
- Authorizer logs: verify token parsed (base64 JSON supported), and scope matches route.
- Confirm header is `Authorization: Bearer <token>` and stage path is correct.

## Runbook commands
- Tail lambda: `aws logs tail /aws/lambda/ttsr-dev-score --since 10m --region eu-west-2`
- Get API URL: `cd infra && terraform output -raw invoke_url`
- Token: `curl -s -X POST "$API/v1/oauth2/token" -H "Content-Type: application/x-www-form-urlencoded" --data 'grant_type=client_credentials&client_id=demo&client_secret=demo-secret&scope=score:write events:read'`

