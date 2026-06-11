import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


BASE = Path(__file__).resolve().parent
SOURCE_DIR = BASE / "difficulty-tagged-json" / "group-d"
OUT_DIR = BASE / "duplicate-audit-json" / "group-d"
SOURCE_FILE = SOURCE_DIR / "group-d-2025-difficulty-tagged.json"
AUDIT_OUT = OUT_DIR / "group-d-2025-duplicate-audit.json"
SUMMARY_OUT = OUT_DIR / "group-d-2025-duplicate-audit-summary.json"
DEDUPED_OUT = OUT_DIR / "group-d-2025-deduped-preview.json"

NEAR_DUPLICATE_THRESHOLD = 0.90
TEMPLATE_VARIANT_TOPICS = {
    "Alphabet Series",
    "Analogy",
    "Coding-Decoding",
    "Mathematical Operations",
    "Number Series",
    "Seating/Ranking Arrangement",
    "Puzzle Arrangement",
    "Simple Interest",
    "Time and Work",
    "Average",
    "Number System",
    "Profit and Loss",
    "Ratio and Proportion",
    "Age Problems",
}


def normalize_text(value: str) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\b\d{3,6}\b$", "", text)
    text = re.sub(r"[^a-z0-9%₹]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def numeric_tokens(value: str) -> list[str]:
    return re.findall(r"₹?\d+(?:\.\d+)?%?", str(value or ""))


def structure_signature(question: dict) -> str:
    text = full_signature(question)
    text = re.sub(r"₹?\d+(?:\.\d+)?%?", "<num>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def question_signature(question: dict) -> str:
    return normalize_text(question.get("question"))


def option_signature(question: dict) -> str:
    options = [normalize_text(option) for option in question.get("options") or []]
    return " | ".join(options)


def full_signature(question: dict) -> str:
    return f"{question_signature(question)} || {option_signature(question)}"


def pair_similarity(left: dict, right: dict) -> float:
    left_text = full_signature(left)
    right_text = full_signature(right)
    if not left_text or not right_text:
        return 0.0
    return SequenceMatcher(None, left_text, right_text).ratio()


def structure_similarity(left: dict, right: dict) -> float:
    left_text = structure_signature(left)
    right_text = structure_signature(right)
    if not left_text or not right_text:
        return 0.0
    return SequenceMatcher(None, left_text, right_text).ratio()


def keep_best(group: list[dict]) -> dict:
    return sorted(
        group,
        key=lambda question: (
            question.get("source_metadata", {}).get("source_pdf", ""),
            question.get("source_metadata", {}).get("question_number", 0),
            question.get("id", ""),
        ),
    )[0]


def group_exact_duplicates(questions: list[dict]) -> list[dict]:
    buckets = defaultdict(list)
    for question in questions:
        buckets[full_signature(question)].append(question)

    groups = []
    for signature, bucket in buckets.items():
        if len(bucket) < 2:
            continue
        keeper = keep_best(bucket)
        groups.append(
            {
                "type": "exact",
                "signature": signature,
                "question_count": len(bucket),
                "keep_id": keeper["id"],
                "duplicate_ids": [question["id"] for question in bucket if question["id"] != keeper["id"]],
                "items": [
                    {
                        "id": question["id"],
                        "subject": question["subject"],
                        "topic": question["topic"],
                        "difficulty": question["difficulty"],
                        "answer": question["answer_label"],
                        "source_pdf": question["source_metadata"]["source_pdf"],
                        "question_number": question["source_metadata"]["question_number"],
                        "question": question["question"],
                    }
                    for question in bucket
                ],
            }
        )
    return groups


def group_near_duplicates(questions: list[dict], exact_duplicate_ids: set[str]) -> tuple[list[dict], list[dict]]:
    review_groups = []
    template_variant_groups = []
    seen_pairs = set()
    buckets = defaultdict(list)
    for question in questions:
        if question["id"] in exact_duplicate_ids:
            continue
        buckets[(question.get("subject"), question.get("topic"))].append(question)

    for bucket in buckets.values():
        for i, left in enumerate(bucket):
            for right in bucket[i + 1 :]:
                pair_key = tuple(sorted([left["id"], right["id"]]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                similarity = pair_similarity(left, right)
                if similarity < NEAR_DUPLICATE_THRESHOLD:
                    continue
                left_numbers = numeric_tokens(left.get("question"))
                right_numbers = numeric_tokens(right.get("question"))
                struct_similarity = structure_similarity(left, right)
                is_template_variant = (
                    (left_numbers != right_numbers and struct_similarity >= 0.92)
                    or (
                        left.get("topic") in TEMPLATE_VARIANT_TOPICS
                        and full_signature(left) != full_signature(right)
                    )
                )
                group = {
                    "type": "near",
                    "similarity": round(similarity, 4),
                    "structure_similarity": round(struct_similarity, 4),
                    "classification": "template_variant_keep" if is_template_variant else "near_duplicate_review",
                    "item_ids": [left["id"], right["id"]],
                    "items": [
                        {
                            "id": question["id"],
                            "subject": question["subject"],
                            "topic": question["topic"],
                            "difficulty": question["difficulty"],
                            "answer": question["answer_label"],
                            "source_pdf": question["source_metadata"]["source_pdf"],
                            "question_number": question["source_metadata"]["question_number"],
                            "question": question["question"],
                        }
                        for question in [left, right]
                    ],
                }
                if group["classification"] == "template_variant_keep":
                    template_variant_groups.append(group)
                else:
                    review_groups.append(group)
    return (
        sorted(review_groups, key=lambda group: group["similarity"], reverse=True),
        sorted(template_variant_groups, key=lambda group: group["similarity"], reverse=True),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])

    exact_groups = group_exact_duplicates(questions)
    exact_duplicate_ids = {
        duplicate_id
        for group in exact_groups
        for duplicate_id in group["duplicate_ids"]
    }
    near_groups, template_variant_groups = group_near_duplicates(questions, exact_duplicate_ids)
    near_candidate_ids = {
        item_id
        for group in near_groups
        for item_id in group["item_ids"]
    }

    deduped_questions = [
        question
        for question in questions
        if question["id"] not in exact_duplicate_ids
    ]

    duplicate_counts_by_subject = Counter()
    for group in exact_groups:
        for item in group["items"]:
            if item["id"] in group["duplicate_ids"]:
                duplicate_counts_by_subject[item["subject"]] += 1

    audit = {
        "exam": payload["exam"],
        "language": payload["language"],
        "source_file": SOURCE_FILE.name,
        "question_count": len(questions),
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "exact_duplicate_groups": exact_groups,
        "near_duplicate_candidate_groups": near_groups,
        "template_variant_keep_groups": template_variant_groups,
    }
    AUDIT_OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    deduped_payload = {
        **{key: value for key, value in payload.items() if key != "questions"},
        "source_layer": SOURCE_FILE.name,
        "dedupe_preview": {
            "method": "remove_exact_duplicates_only",
            "removed_exact_duplicate_questions": len(exact_duplicate_ids),
            "near_duplicates_not_removed": len(near_groups),
            "template_variants_not_removed": len(template_variant_groups),
        },
        "question_count": len(deduped_questions),
        "questions": deduped_questions,
    }
    DEDUPED_OUT.write_text(json.dumps(deduped_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "exam": payload["exam"],
        "language": payload["language"],
        "source_file": SOURCE_FILE.name,
        "question_count": len(questions),
        "exact_duplicate_groups": len(exact_groups),
        "exact_duplicate_questions_to_remove": len(exact_duplicate_ids),
        "deduped_preview_question_count": len(deduped_questions),
        "near_duplicate_candidate_groups": len(near_groups),
        "near_duplicate_candidate_questions": len(near_candidate_ids),
        "template_variant_keep_groups": len(template_variant_groups),
        "duplicate_counts_by_subject": dict(sorted(duplicate_counts_by_subject.items())),
        "output_files": [
            AUDIT_OUT.name,
            SUMMARY_OUT.name,
            DEDUPED_OUT.name,
        ],
        "notes": [
            "Exact duplicates are safe to remove in the deduped preview.",
            "Near duplicates are audit candidates only and are not removed automatically.",
            "Template variants are similar question patterns with different numeric values and are kept.",
            "Similarity is computed within the same subject/topic using normalized question plus options.",
        ],
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
