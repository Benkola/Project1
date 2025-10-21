import os, json, time, hmac, hashlib, base64, uuid
def _hmac(data: str) -> str:
    return hmac.new(os.environ["AUTH_SIGNING_SECRET"].encode(), data.encode(), hashlib.sha256).hexdigest()

def _make_token(client_id: str, scopes: list[str]) -> dict:
    ttl = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))
    exp = int(time.time()) + ttl
    j = {"cid": client_id, "scp": scopes, "exp": exp, "jti": str(uuid.uuid4())}
    payload = base64.urlsafe_b64encode(json.dumps(j).encode()).decode().rstrip("=")
    sig = _hmac(payload)
    return {"access_token": f"{payload}.{sig}", "token_type": "bearer", "expires_in": ttl, "scope": " ".join(scopes)}

def handler(event, context):
    # expects form-encoded body: grant_type=client_credentials&client_id=...&client_secret=...&scope=...
    body = event.get("body") or ""
    params = {}
    for part in body.split("&"):
        if "=" in part:
            k,v = part.split("=",1)
            params[k] = v

    if params.get("grant_type") != "client_credentials":
        return _resp(400, {"error":"unsupported_grant_type"})

    client_id = params.get("client_id") or ""
    client_secret = params.get("client_secret") or ""
    requested = (params.get("scope") or "").split()

    clients = json.loads(os.getenv("AUTH_CLIENTS_JSON",'{"demo":{"secret":"demo-secret","scopes":["score:write","events:read"]}}'))
    c = clients.get(client_id)
    if not c or c.get("secret") != client_secret:
        return _resp(401, {"error":"invalid_client"})

    scopes = requested or c.get("scopes", [])
    token = _make_token(client_id, scopes)
    return _resp(200, token)

def _resp(code, obj):
    return {"statusCode":code,"headers":{"Content-Type":"application/json"},"body":json.dumps(obj)}
