# TTSR PRD (v1)
Problem: Fragmented travel signals; no unified risk score for trust & safety triage.
Users: Booking platforms, ops analysts, fraud/T&S teams.
Use cases: (1) Score a booking event; (2) Receive signed webhook; (3) Fetch audit record.
Non-goals: Real-time PII processing; full ML; multi-tenant billing.
Success: p95 < 450ms; 99.9% uptime; false positive < 5% (rules v0, offline eval).
SLOs: availability 99.9%; p95 latency 450ms; 5xx < 1%.
Guardrails: GDPR-first—no PII; DPIA-lite attached.
