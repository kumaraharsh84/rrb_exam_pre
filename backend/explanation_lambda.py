from __future__ import annotations

import json
import os
import time
import boto3
from botocore.exceptions import ClientError

from explanation_common import (
    GENERATION_VERSION,
    generate_explanation,
    normalize_for_json,
    normalize_text,
    question_hash,
    utc_now,
)

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
EXPLANATIONS_TABLE = os.getenv("EXPLANATIONS_TABLE", "rrb_explanations")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(EXPLANATIONS_TABLE)


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(normalize_for_json(body), ensure_ascii=False),
    }


def parse_event_body(event: dict) -> dict:
    body = event.get("body") if isinstance(event, dict) else event
    if isinstance(body, str):
        parsed = json.loads(body or "{}")
    elif isinstance(body, dict):
        parsed = body
    else:
        raise ValueError("Invalid payload format")

    if not isinstance(parsed, dict):
        raise ValueError("Payload body must be a dictionary")
    return parsed


def get_by_question_id(question_id: str) -> dict | None:
    if not question_id:
        return None
    result = table.get_item(Key={"question_id": question_id})
    return result.get("Item")


def get_by_question_hash(q_hash: str) -> dict | None:
    if not q_hash or len(q_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in q_hash):
        return None
    result = table.query(
        IndexName="question_hash-index",
        KeyConditionExpression="question_hash = :hash",
        ExpressionAttributeValues={":hash": q_hash},
        Limit=1,
    )
    items = result.get("Items") or []
    return items[0] if items else None


def cache_response(item: dict, cached: bool = True) -> dict:
    return {
        "cached": cached,
        "questionId": item.get("question_id"),
        "questionHash": item.get("question_hash"),
        "explanation": item.get("explanation"),
        "generatedAt": item.get("created_at"),
        "generationModel": item.get("generation_model"),
        "generationVersion": item.get("generation_version"),
        "subject": item.get("subject"),
        "topic": item.get("topic"),
    }


def lambda_handler(event, context):
    method = (event or {}).get("requestContext", {}).get("http", {}).get("method") or (event or {}).get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    try:
        payload = parse_event_body(event or {})
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Payload parsing error: {e}")
        return response(400, {"error": "Invalid payload format"})

    question = normalize_text(payload.get("question"))
    options = payload.get("options") or []
    if not question or len(options) != 4:
        return response(400, {"error": "question and exactly 4 options are required"})

    question_id = str(payload.get("questionId") or "").strip()
    q_hash = question_hash(payload)

    try:
        cached_item = get_by_question_id(question_id) or get_by_question_hash(q_hash)
        if cached_item:
            return response(200, cache_response(cached_item, cached=True))

        explanation, model_used = generate_explanation(payload)
        now = utc_now()
        ttl_val = int(time.time()) + 90 * 86400  # 90 days from now
        item = {
            "question_id": question_id or f"hash_{q_hash[:16]}",
            "question_hash": q_hash,
            "explanation": explanation,
            "subject": payload.get("subject"),
            "topic": payload.get("topic"),
            "created_at": now,
            "updated_at": now,
            "generation_model": model_used,
            "generation_version": GENERATION_VERSION,
            "ttl": ttl_val,
        }
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(question_id)",
        )
        return response(200, cache_response(item, cached=False))
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        print(f"AWS ClientError: {error}")
        return response(500, {"error": "Explanation service AWS error", "code": code})
    except Exception as error:
        print(f"Unexpected Lambda error: {error}")
        return response(500, {"error": "Explanation service failed"})
