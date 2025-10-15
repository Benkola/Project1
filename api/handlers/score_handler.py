import os, boto3
from botocore.exceptions import ClientError
from .utils import parse_body, get_header, score_signals, json_dumps, now_ts, TENANT, SCORE_VERSION, make_trace_id

dynamodb = boto3.resource("dynamodb")
TABLE = dynamodb.Table(os.getenv("TABLE", "ttsr-events"))

def handler(event, context):
    trace_id = make_trace_id()
    body = parse_body(event)
    idem = get_header(event, "Idempotency-Key")
    if not body or not body.get("event_id") or not idem:
        return _resp(400, {"code":"bad_request","message":"Missing event_id or Idempotency-Key","trace_id":trace_id})

    event_id = body["event_id"]
    pk, sk = f"tenant#{TENANT}", f"evt#{event_id}"

    # Idempotency check (same idempotency_key returns same result)
    try:
        existing = TABLE.get_item(Key={"pk": pk, "sk": sk}).get("Item")
    except ClientError as e:
        return _resp(500, {"code":"dynamo_error","message":str(e),"trace_id":trace_id})

    if existing and existing.get("idempotency_key") == idem:
        return _resp(202, {"event_id":event_id,"score":existing["score"],"action":existing["action"],"trace_id":trace_id})

    score, action = score_signals(body.get("signals", {}))
    item = {
        "pk": pk,
        "sk": sk,
        "source": body.get("source","unknown"),
        "ts": now_ts(),
        "signals": body.get("signals", {}),
        "score_v": SCORE_VERSION,
        "score": score,
        "action": action,
        "idempotency_key": idem,
        "status": "scored"
    }
    try:
        # Put item; if a different idem_key exists, we still overwrite — v1 simple semantics
        TABLE.put_item(Item=item)
    except ClientError as e:
        return _resp(500, {"code":"dynamo_error","message":str(e),"trace_id":trace_id})

    return _resp(202, {"event_id":event_id,"score":score,"action":action,"trace_id":trace_id})

def _resp(code: int, obj: dict):
    return {"statusCode": code, "headers":{"Content-Type":"application/json"}, "body": json_dumps(obj)}
