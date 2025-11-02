# TTSR Golden Flow (<3 minutes)

## Prep
- Set `API=$(terraform -chdir=infra output -raw invoke_url)` (Terminal).
- In Postman, set base URL to the same.

## 1) Health (no auth)
```bash
curl -s "$API/v1/health" | jq
# -> { "status": "ok", "ts": <epoch> }

