from __future__ import annotations

import json
from pathlib import Path

from explanation_common import (
    GENERATION_VERSION,
    generate_explanation,
    normalize_text,
    question_hash,
    utc_now,
)

BACKEND_ROOT = Path(__file__).resolve().parent
DATA_DIR = BACKEND_ROOT / "data"
EXPLANATION_CACHE_PATH = DATA_DIR / "explanations.json"

_cache_by_id = {}
_cache_by_hash = {}
_cache_loaded = False


def populate_indices(cache_data: dict):
    global _cache_by_id, _cache_by_hash
    _cache_by_id.clear()
    _cache_by_hash.clear()
    for item in cache_data.get("items") or []:
        q_id = item.get("question_id")
        q_hash = item.get("question_hash")
        if q_id:
            _cache_by_id[q_id] = item
        if q_hash:
            _cache_by_hash[q_hash] = item


def load_cache() -> dict:
    global _cache_loaded
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not EXPLANATION_CACHE_PATH.exists():
        data = {"version": 1, "items": []}
    else:
        try:
            data = json.loads(EXPLANATION_CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"version": 1, "items": []}

    if not (isinstance(data, dict) and isinstance(data.get("items"), list)):
        data = {"version": 1, "items": []}

    populate_indices(data)
    _cache_loaded = True
    return data


def save_cache(cache: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPLANATION_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    populate_indices(cache)


def find_cached(cache: dict, question_id: str, q_hash: str) -> dict | None:
    if not _cache_loaded:
        load_cache()
    if question_id and question_id in _cache_by_id:
        return _cache_by_id[question_id]
    if q_hash and q_hash in _cache_by_hash:
        return _cache_by_hash[q_hash]
    return None


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
