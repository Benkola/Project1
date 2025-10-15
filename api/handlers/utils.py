import json, os, time, hmac, hashlib, decimal, uuid

TENANT = os.getenv("TENANT", "demo")
SCORE_VERSION = "v0_rules"

def json_dumps(data: dict) -> str:
    class DEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                return float(o)
            return super().default(o)
    return json.dumps(data, cls=DEncoder)

def parse_body(event) -> dict:
    body = event.get("body")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    return body or {}

def get_header(event, name: str) -> str:
    headers = event.get("headers") or {}
    # case-insensitive
    for k,v in headers.items():
        if k.lower() == name.lower():
            return v
    return ""

def score_signals(signals: dict) -> tuple[float, str]:
    """Deterministic rule-based scorer (0..100) with allow/review/hold."""
    weights = {"delay":30, "weather":25, "geo":25, "payment":20}
    total = 0.0
    for k, w in weights.items():
        v = float(signals.get(k, 0) or 0)
        v = max(0.0, min(1.0, v))  # clamp
        total += w * v
    score = round(min(100.0, total / 1.0), 1)
    action = "allow" if score < 30 else "review" if score < 60 else "hold"
    return score, action

def now_ts() -> int:
    return int(time.time())

def make_trace_id() -> str:
    # simple placeholder; X-Ray will override in AWS
    return str(uuid.uuid4())

def sign_webhook(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
