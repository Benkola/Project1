from .utils import json_dumps, now_ts

def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json_dumps({"status":"ok","ts": now_ts()})
    }
