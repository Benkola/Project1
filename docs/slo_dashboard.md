# SLOs & Alerts (v1)

## SLOs (monthly)
- Availability: **99.9%** (error budget ~43m/mo). Proxy: 5xx rate at API Gateway < 0.1% of requests.
- Latency: **p95 ≤ 450ms**. Alert if p95 > 600ms for 10m.
- Error rate: **< 2%** 5xx for 10m.
- (Optional) DLQ depth: **= 0** (webhooks disabled by default).

## Signals & thresholds
- API Gateway `5XXError` (Sum) / `Count` → error rate.
- API Gateway `Latency` with **extended statistic p95**.
- Lambda `Errors` (Sum) and `Duration` p95.
- Dashboard: Stage = `dev`, Region = `eu-west-2`.

## Alert policy
- **High**: 5xx error rate ≥ 5% for 10 minutes.
- **Medium**: p95 latency ≥ 600ms for 10 minutes.
- **Medium**: Lambda Errors ≥ 5 for 5 minutes.

## Error budget approach
- Track monthly minutes with 5xx rate > 0.1% or health fails.
- If >50% of budget burned mid-cycle → feature freeze; prioritise reliability.

