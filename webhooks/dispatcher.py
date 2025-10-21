import json, os, urllib.request, urllib.error, hmac, hashlib

def sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def deliver(url: str, secret: str, body: dict) -> tuple[int,str]:
    payload = json.dumps(body)
    sig = sign(secret, payload)
    req = urllib.request.Request(
        url=url,
        data=payload.encode(),
        headers={
            "Content-Type":"application/json",
            "User-Agent":"ttsr-webhook/1.0",
            "X-TTSR-Signature": sig
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.getcode(), resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200] if e.fp else str(e)
    except Exception as e:
        return 0, str(e)
