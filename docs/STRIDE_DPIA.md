## STRIDE
| Threat | Example | Mitigation |
|---|---|---|
| Spoofing | Fake client token | OAuth2 Client Credentials, rotate creds |
| Tampering | Payload altered | HMAC-SHA256 on webhooks, TLS, conditional writes |
| Repudiation | Client denies request | Audit logs (client_id, trace_id, IP) |
| Info Disclosure | PII leaks in logs | No PII, secrets masked, least privilege |
| DoS | Request floods | Rate limits, WAF (later), exponential backoff |
| Elevation | Scope abuse | RBAC scopes per token, least-priv IAM |

## DPIA-Lite
- Data: event metadata & numeric signals; no direct identifiers.
- Purpose: produce risk score + action for T&S triage.
- Lawful basis: legitimate interests (demo).
- Risks: free-text signals → re-identification; Control: restrict to numeric keys.
- Controls: schema validation, short retention (e.g., 30 days), access logging, KMS for secrets.
- Review: re-assess before ML or any PII is introduced.
