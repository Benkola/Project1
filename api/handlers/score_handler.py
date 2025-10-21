import os, json, time, hmac, hashlib, random
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

# -------- simple helpers --------
def json_dumps(x): return json.dumps(x, separators=(",", ":"), ensure_ascii=False)
def now_ts(): return int(time.time())
def get_header(event, name):
    h = event.get("headers") or {}
    for k, v in h.items():
        if isinstance(k, str) and k.lower() == name.lower():
            return v
    return None
def parse_body(event):
    b = event.get("body")
    if not b: return {}
    try:
        return json.loads(b)
    except Exception:
        return {}
def make_trace_id():
    return f"1-{now_ts():x}-{random.getrandbits(64):016x}"

# Convert floats -> Decimal recursively (DynamoDB requirement)
def to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [to_decimal(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    return obj

# Feature flag for policy weights
VARIANT = os.getenv("POLICY_VARIANT", "default").lower()
if VARIANT == "alt":
    WEIGHTS = {"delay": 20, "weather": 35, "geo": 35, "payment": 10}
else:
    WEIGHTS = {"delay": 30, "weather": 25, "geo": 25, "payment": 20}

SCORE_VERSION = "v0_rules"

def score_signals(signals: dict):
    total = 0.0
    for k, w in WEIGHTS.items():
        v = float(signals.get(k, 0) or 0)
        total += w * v
    s = min(100.0, max(0.0, total / 100.0))
    action = "allow" if s < 30 else ("review" if s < 60 else "hold")
    return round(s, 1), action

# ---- Lazy DynamoDB table getter (so tests don't need AWS/region) ----
def get_table():
    table_name = os.getenv("TABLE", "ttsr-events")
    # pick a region from env, else default to your deployed region for local tests
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "eu-west-2"
    ddb = boto3.resource("dynamodb", region_name=region)
    return ddb.Table(table_name)

TENANT = os.getenv("TENANT", "demo")

# -------- webhook helper (optional) --------
def _maybe_webhook(payload: dict):
    url = os.getenv("WEBHOOK_URL", "")
    secret = os.getenv("WEBHOOK_SECRET", "")
    if not (url and secret):
        return
    try:
        import urllib.request
        body = json_dumps(payload)
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        req = urllib.request.Request(
            url=url, data=body.encode(), method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ttsr-webhook/1.0",
                "X-TTSR-Signature": sig
            }
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        # swallow errors in v1
        pass

# ---- Rate-limit headers (demo values) ----
def _rl_headers():
    reset = now_ts() + 60
    return {
        "X-RateLimit-Limit": "1000",
        "X-RateLimit-Remaining": "999",
        "X-RateLimit-Reset": str(reset)
    }

def _resp(code, obj):
    h = {"Content-Type": "application/json"}
    h.update(_rl_headers())
    return {"statusCode": code, "headers": h, "body": json_dumps(obj)}

# -------- Lambda handler --------
def handler(event, context):
    trace_id = make_trace_id()
    body = parse_body(event)
    idem = get_header(event, "Idempotency-Key")

    if not body or not body.get("event_id") or not idem:
        return _resp(400, {"code":"bad_request","message":"Missing event_id or Idempotency-Key","trace_id":trace_id})

    event_id = body["event_id"]
    pk, sk = f"tenant#{TENANT}", f"evt#{event_id}"

    table = get_table()

    # idempotency read
    try:
        existing = table.get_item(Key={"pk": pk, "sk": sk}).get("Item")
    except ClientError as e:
        return _resp(500, {"code":"dynamo_error","message":str(e),"trace_id":trace_id})

    if existing and existing.get("idempotency_key") == idem:
        return _resp(202, {"event_id":event_id,"score":float(existing["score"]), "action":existing["action"],"trace_id":trace_id})

    # compute score
    score, action = score_signals(body.get("signals", {}))
    signals_ddb = to_decimal(body.get("signals", {}))

    item = {
        "pk": pk, "sk": sk,
        "tenant": TENANT,
        "source": body.get("source","unknown"),
        "ts": now_ts(),
        "signals": signals_ddb,
        "score_v": SCORE_VERSION,
        "score": Decimal(str(score)),
        "action": action,
        "idempotency_key": idem,
        "status": "scored"
    }
    try:
        table.put_item(Item=item)
    except ClientError as e:
        return _resp(500, {"code":"dynamo_error","message":str(e),"trace_id":trace_id})

    _maybe_webhook({
        "type":"risk.scored",
        "event_id": event_id,
        "score": float(score),
        "action": action,
        "score_v": SCORE_VERSION
    })

    return _resp(202, {"event_id":event_id,"score":float(score),"action":action,"trace_id":trace_id})
