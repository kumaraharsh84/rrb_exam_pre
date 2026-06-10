from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")
NOVA_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "apac.amazon.nova-pro-v1:0")
LLAMA_MODEL_ID = os.getenv("LLAMA_MODEL_ID", "us.meta.llama3-1-70b-instruct-v1:0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EXPLANATIONS_TABLE = os.getenv("EXPLANATIONS_TABLE", "rrb_explanations")
GENERATION_VERSION = os.getenv("EXPLANATION_GENERATION_VERSION", "eis-v1")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(EXPLANATIONS_TABLE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_text(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalize_for_json(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [normalize_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_for_json(item) for key, item in value.items()}
    return value


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
        return json.loads(body or "{}")
    if isinstance(body, dict):
        return body
    return {}


def question_hash(payload: dict) -> str:
    canonical = {
        "question": normalize_text(payload.get("question")),
        "options": [normalize_text(option) for option in payload.get("options") or []],
        "answer": payload.get("answer"),
        "correctAnswer": normalize_text(payload.get("correctAnswer")),
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def answer_label(payload: dict) -> str:
    answer = payload.get("answer")
    options = payload.get("options") or []
    if isinstance(answer, int) and 0 <= answer < len(options):
        return f"{chr(ord('A') + answer)}. {options[answer]}"
    return str(payload.get("correctAnswer") or answer or "")


def build_prompt(payload: dict) -> str:
    subject = payload.get("subject") or "General"
    topic = payload.get("topic") or "General"
    difficulty = payload.get("difficulty") or "medium"
    options = payload.get("options") or []
    option_lines = "\n".join(f"- {option}" for option in options)

    subject_rules = {
        "Mathematics": "Return Formula, Step 1, Step 2, and Final Answer. Show calculations clearly.",
        "General Intelligence and Reasoning": "Return Pattern, Logic, Elimination Process when useful, and Final Answer.",
        "General Intelligence & Reasoning": "Return Pattern, Logic, Elimination Process when useful, and Final Answer.",
        "General Awareness": "Return Correct Fact, Short Context, and Final Answer. Avoid uncertain or outdated claims.",
        "General Science": "Return Concept, Reasoning, and Final Answer. Keep the science explanation concise.",
    }
    rules = subject_rules.get(subject, "Explain the answer in simple exam-oriented language.")

    return f"""
You are generating an explanation for an RRB exam preparation app.

Write a clear solution for the MCQ below.

Rules:
- Explain why the correct answer is correct.
- Explain why other options are incorrect only when useful.
- Use simple exam-oriented language.
- Avoid unnecessary theory.
- Keep the explanation within 150-250 words.
- Do not invent facts beyond the question.
- {rules}

Question:
{payload.get("question")}

Options:
{option_lines}

Correct answer:
{answer_label(payload)}

Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

Return only the explanation text. Do not return JSON.
""".strip()


def generate_explanation(payload: dict) -> str:
    import urllib.request
    subject = payload.get("subject") or "General"
    prompt = build_prompt(payload)
    
    # Normalize subject for routing
    subj_lower = (subject or "").lower()
    is_general_awareness = "awareness" in subj_lower or "current affairs" in subj_lower
    is_math_or_reasoning = "math" in subj_lower or "reasoning" in subj_lower or "mental ability" in subj_lower

    if is_general_awareness and GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        req_payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700}
        }
        req = urllib.request.Request(url, data=json.dumps(req_payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Gemini API Error: {e}. Falling back to Bedrock.")

    active_model_id = LLAMA_MODEL_ID if is_math_or_reasoning else NOVA_MODEL_ID
    
    if "llama3" in active_model_id.lower():
        body = json.dumps({
            "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
            "max_gen_len": 700,
            "temperature": 0.2,
            "top_p": 0.9
        })
    else:
        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"max_new_tokens": 700, "temperature": 0.2}
        })

    response_payload = bedrock.invoke_model(
        modelId=active_model_id,
        body=body
    )
    result = json.loads(response_payload["body"].read())
    
    if "llama3" in active_model_id.lower():
        return result.get("generation", "").strip()
    return result["output"]["message"]["content"][0]["text"].strip()


def get_by_question_id(question_id: str) -> dict | None:
    if not question_id:
        return None
    result = table.get_item(Key={"question_id": question_id})
    return result.get("Item")


def get_by_question_hash(q_hash: str) -> dict | None:
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
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})

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

        explanation = generate_explanation(payload)
        now = utc_now()
        item = {
            "question_id": question_id or f"hash_{q_hash[:16]}",
            "question_hash": q_hash,
            "explanation": explanation,
            "subject": payload.get("subject"),
            "topic": payload.get("topic"),
            "created_at": now,
            "updated_at": now,
            "generation_model": "Multi-Model-Router",
            "generation_version": GENERATION_VERSION,
        }
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(question_id)",
        )
        return response(200, cache_response(item, cached=False))
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        return response(500, {"error": "Explanation service AWS error", "details": code})
    except Exception as error:
        return response(500, {"error": "Explanation service failed", "details": str(error)})
