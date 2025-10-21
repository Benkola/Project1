import os, json
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

DDB = boto3.resource("dynamodb")
TABLE = DDB.Table(os.getenv("TABLE", "ttsr-events"))
TENANT = os.getenv("TENANT", "demo")

def to_jsonable(obj):
    # Convert DynamoDB Decimals recursively to floats (or ints if integral)
    if isinstance(obj, Decimal):
        # Try to return an int if it is integral (e.g., timestamps)
        if obj == obj.to_integral_value():
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    return obj

def handler(event, context):
    event_id = (event.get("pathParameters") or {}).get("id")
    if not event_id:
        return _resp(400, {"code":"bad_request","message":"Missing path id"})

    pk, sk = f"tenant#{TENANT}", f"evt#{event_id}"
    try:
        res = TABLE.get_item(Key={"pk": pk, "sk": sk})
    except ClientError as e:
        return _resp(500, {"code":"dynamo_error","message":str(e)})

    item = res.get("Item")
    if not item:
        return _resp(404, {"code":"not_found","message":"No such event"})

    # Flatten + convert Decimals
    out = {
        "id": event_id,
        "tenant": TENANT,
        "source": item.get("source"),
        "ts": to_jsonable(item.get("ts")),
        "signals": to_jsonable(item.get("signals", {})),
        "score_v": item.get("score_v"),
        "score": to_jsonable(item.get("score")),
        "action": item.get("action"),
        "idempotency_key": item.get("idempotency_key"),
        "status": item.get("status"),
    }
    return _resp(200, out)

def _resp(code, obj):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(obj, separators=(",", ":"))
    }
