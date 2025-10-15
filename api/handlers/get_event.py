import os, boto3
from botocore.exceptions import ClientError
from .utils import json_dumps, TENANT

dynamodb = boto3.resource("dynamodb")
TABLE = dynamodb.Table(os.getenv("TABLE", "ttsr-events"))

def handler(event, context):
    event_id = (event.get("pathParameters") or {}).get("id")
    if not event_id:
        return _resp(400, {"code":"bad_request","message":"Missing event id"})
    pk, sk = f"tenant#{TENANT}", f"evt#{event_id}"
    try:
        res = TABLE.get_item(Key={"pk":pk, "sk":sk})
    except ClientError as e:
        return _resp(500, {"code":"dynamo_error","message":str(e)})
    item = res.get("Item")
    if not item:
        return _resp(404, {"code":"not_found","message":"Event not found"})
    # Present a friendly shape
    out = {
        "id": event_id,
        "tenant": TENANT,
        "source": item.get("source"),
        "ts": item.get("ts"),
        "signals": item.get("signals"),
        "score_v": item.get("score_v"),
        "score": item.get("score"),
        "action": item.get("action"),
        "idempotency_key": item.get("idempotency_key"),
        "status": item.get("status"),
    }
    return _resp(200, out)

def _resp(code: int, obj: dict):
    return {"statusCode": code, "headers":{"Content-Type":"application/json"}, "body": json_dumps(obj)}
