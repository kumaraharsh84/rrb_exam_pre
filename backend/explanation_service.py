from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3


BACKEND_ROOT = Path(__file__).resolve().parent
DATA_DIR = BACKEND_ROOT / "data"
EXPLANATION_CACHE_PATH = DATA_DIR / "explanations.json"

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")
NOVA_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "apac.amazon.nova-pro-v1:0")
LLAMA_MODEL_ID = os.getenv("LLAMA_MODEL_ID", "us.meta.llama3-1-70b-instruct-v1:0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GENERATION_VERSION = "eis-v1"

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_text(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def question_hash(payload: dict) -> str:
    canonical = {
        "question": normalize_text(payload.get("question")),
        "options": [normalize_text(option) for option in payload.get("options") or []],
        "answer": payload.get("answer"),
        "correctAnswer": normalize_text(payload.get("correctAnswer")),
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cache() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not EXPLANATION_CACHE_PATH.exists():
        return {"version": 1, "items": []}

    try:
        data = json.loads(EXPLANATION_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "items": []}

    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data
    return {"version": 1, "items": []}


def save_cache(cache: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPLANATION_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def find_cached(cache: dict, question_id: str, q_hash: str) -> dict | None:
    items = cache.get("items") or []
    if question_id:
        for item in items:
            if item.get("question_id") == question_id:
                return item

    for item in items:
        if item.get("question_hash") == q_hash:
            return item
    return None


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


def generate_explanation(payload: dict) -> tuple[str, str]:
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
                text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text, "gemini-2.5-flash"
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
        text = result.get("generation", "").strip()
    else:
        text = result["output"]["message"]["content"][0]["text"].strip()
        
    return text, active_model_id


def generate_local_mock_explanation(payload: dict) -> str:
    question = payload.get("question", "")
    options = payload.get("options") or []
    answer = payload.get("answer")
    correct_text = ""
    if isinstance(answer, int) and 0 <= answer < len(options):
        correct_text = options[answer]
    else:
        correct_text = str(payload.get("correctAnswer") or answer or "")

    subject = payload.get("subject") or "General"
    topic = payload.get("topic") or "General"
    
    subj_lower = subject.lower()
    if "math" in subj_lower or "reasoning" in subj_lower or "intelligence" in subj_lower:
        return f"""[Local Dev Mode - Math/Reasoning Solution]
Formula/Logic: Solve using standard {topic} principles.
Step 1: Identify details from the question stem: "{question}".
Step 2: Solve step-by-step:
  - Analyze parameters: options provided are {", ".join(options)}.
  - Apply logical derivation to determine the correct value.
Step 3: The calculated result is {correct_text}.
Final Answer: Therefore, the correct option is {correct_text}."""
    else:
        return f"""[Local Dev Mode - GK/Science Context]
Concept: Core concepts in {subject} - {topic}.
Explanation: The question asks: "{question}".
Fact: The correct answer is {correct_text}.
Context: The other options ({", ".join([opt for opt in options if opt != correct_text])}) represent incorrect details, alternate categories, or different contexts. This question tests standard historical, static, or scientific facts relevant to the RRB syllabus.
Summary: Remember that {correct_text} matches the query perfectly."""


def get_or_create_explanation(payload: dict) -> dict:
    question = normalize_text(payload.get("question"))
    options = payload.get("options") or []
    if not question or len(options) != 4:
        return {
            "statusCode": 400,
            "body": {
                "error": "question and exactly 4 options are required",
            },
        }

    question_id = str(payload.get("questionId") or "").strip()
    q_hash = question_hash(payload)
    cache = load_cache()
    cached = find_cached(cache, question_id, q_hash)
    if cached:
        return {
            "statusCode": 200,
            "body": {
                "cached": True,
                "questionId": cached.get("question_id"),
                "questionHash": cached.get("question_hash"),
                "explanation": cached.get("explanation"),
                "generatedAt": cached.get("created_at"),
                "generationModel": cached.get("generation_model"),
                "generationVersion": cached.get("generation_version"),
                "subject": cached.get("subject"),
                "topic": cached.get("topic"),
            },
        }

    try:
        explanation, model_used = generate_explanation(payload)
    except Exception as e:
        print(f"Bedrock/Gemini generation failed: {e}. Generating local fallback mock explanation.")
        explanation = generate_local_mock_explanation(payload)
        model_used = "local-mock-explainer"

    now = utc_now()
    record = {
        "id": f"exp_{q_hash[:16]}",
        "question_id": question_id or f"hash_{q_hash[:16]}",
        "question_hash": q_hash,
        "explanation": explanation,
        "subject": payload.get("subject"),
        "topic": payload.get("topic"),
        "created_at": now,
        "updated_at": now,
        "generation_model": model_used,
        "generation_version": GENERATION_VERSION,
    }
    cache.setdefault("items", []).append(record)
    save_cache(cache)

    return {
        "statusCode": 200,
        "body": {
            "cached": False,
            "questionId": record["question_id"],
            "questionHash": q_hash,
            "explanation": explanation,
            "generatedAt": now,
            "generationModel": model_used,
            "generationVersion": GENERATION_VERSION,
            "subject": payload.get("subject"),
            "topic": payload.get("topic"),
        },
    }
