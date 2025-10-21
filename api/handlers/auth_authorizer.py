import os, json, hmac, hashlib, sys, base64

SECRET = os.getenv("AUTH_SIGNING_SECRET", "change-me-please")

def log(**kw):
    try:
        print(json.dumps(kw), file=sys.stdout)
    except Exception:
        print(str(kw), file=sys.stdout)

def _deny(principal="anonymous", resource="*"):
    log(decision="DENY", principal=principal, resource=resource)
    return {
        "principalId": principal,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": "Deny",
                "Resource": [resource]
            }]
        },
        "context": {"reason": "unauthorized"}
    }

def _allow(principal, resource, ctx=None):
    log(decision="ALLOW", principal=principal, resource=resource, ctx=ctx or {})
    return {
        "principalId": principal,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": "Allow",
                "Resource": [resource]
            }]
        },
        "context": ctx or {}
    }

def _parse_bearer(event):
    # TOKEN authorizer: event["authorizationToken"] is usually "Bearer <token>"
    t = event.get("authorizationToken")
    if isinstance(t, str) and t.lower().startswith("bearer "):
        return t[7:].strip()
    # Fallback for REQUEST-style
    headers = event.get("headers") or {}
    for k, v in headers.items():
        if isinstance(k, str) and k.lower() == "authorization" and isinstance(v, str) and v.lower().startswith("bearer "):
            return v[7:].strip()
    return None

def _json_from_payload_str(payload_str: str):
    # Try raw JSON first
    try:
        return json.loads(payload_str)
    except Exception:
        pass
    # Then base64/urlsafe-base64 JSON (common for compact tokens)
    try:
        s = payload_str.encode()
        # Pad for base64 if missing
        pad = (-len(s)) % 4
        s = s + b"=" * pad
        decoded = base64.urlsafe_b64decode(s).decode()
        return json.loads(decoded)
    except Exception as e:
        raise ValueError(f"payload_parse_failed: {e}")

def _verify_token(token):
    """
    Token format: <payload>.<hex_hmac>, where <payload> is either:
      - raw JSON string, or
      - base64/urlsafe-base64 encoded JSON string

    HMAC is computed over the <payload> bytes exactly as they appear in the token.
    """
    try:
        if "." not in token:
            return None
        payload_str, sig_hex = token.rsplit(".", 1)

        expected = hmac.new(SECRET.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig_hex):
            log(sig_mismatch=True)
            return None

        payload = _json_from_payload_str(payload_str)

        # scopes can be in scp (list), scopes (list) or scope (space-delimited str)
        if isinstance(payload.get("scp"), list):
            scopes = payload["scp"]
        elif isinstance(payload.get("scopes"), list):
            scopes = payload["scopes"]
        elif isinstance(payload.get("scope"), str):
            scopes = payload["scope"].split()
        else:
            scopes = []

        cid = payload.get("cid", "unknown")
        return {"cid": cid, "scopes": set(scopes), "raw": payload}
    except Exception as e:
        log(verify_error=str(e))
        return None

def _parse_method_arn(methodArn):
    # arn:aws:execute-api:<region>:<account>:<apiId>/<stage>/<verb>/<path...>
    parts = methodArn.split(":")
    region  = parts[3]
    account = parts[4]
    rest    = parts[5]  # apiId/stage/VERB/path...
    elems   = rest.split("/")
    api_id, stage, verb = elems[0], elems[1], elems[2]
    path_parts = elems[3:]
    path = "/" + "/".join(path_parts) if path_parts else "/"
    return region, account, api_id, stage, verb.upper(), path

def handler(event, context):
    methodArn = event.get("methodArn", "*")
    log(event_seen=True, methodArn=methodArn, type=event.get("type"))

    token = _parse_bearer(event)
    if not token:
        return _deny(methodArn)

    v = _verify_token(token)
    if not v:
        return _deny(methodArn)

    scopes = v["scopes"]
    region, account, api_id, stage, verb, path = _parse_method_arn(methodArn)
    log(parsed=dict(region=region, account=account, api_id=api_id, stage=stage, verb=verb, path=path), scopes=list(scopes))

    base = f"arn:aws:execute-api:{region}:{account}:{api_id}/{stage}/{verb}"

    # Route -> required scope + allowed resource
    if verb == "POST" and path == "/v1/score":
        need = "score:write"
        resource = f"{base}/v1/score"    # exact
    elif verb == "GET" and path.startswith("/v1/events/"):
        need = "events:read"
        resource = f"{base}/v1/events/*" # wildcard for any id
    else:
        return _deny(methodArn)

    if need in scopes:
        ctx = {"client_id": v["cid"], "scopes": " ".join(sorted(scopes))}
        return _allow(v["cid"], resource, ctx=ctx)

    return _deny(methodArn)
