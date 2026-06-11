import json
import re
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parent
SOURCE_FILE = BASE / "duplicate-audit-json" / "technician-grade-3" / "technician-grade-3-2026-deduped-preview.json"
FRONTEND_BANK = PROJECT_ROOT / "frontend" / "data" / "question-bank.json"
OUT_DIR = BASE / "app-merge-json" / "technician-grade-3"
APP_MERGE_OUT = OUT_DIR / "technician-grade-3-2026-app-merge.json"
MERGED_PREVIEW_OUT = OUT_DIR / "question-bank-with-technician-grade-3-2026-preview.json"
SUMMARY_OUT = OUT_DIR / "technician-grade-3-2026-app-merge-summary.json"


DIFFICULTY_TO_APP = {
    "basic": "easy",
    "intermediate": "medium",
    "advanced": "hard",
}

TOPIC_TO_APP = {
    "Age Problems": "Age Calculation Problems",
    "Algebra": "Elementary Algebra - Linear Equations",
    "Alphabet Series": "Alphabetical Series",
    "Analogy": "Analogy - Letter Based",
    "Art and Culture": "Art & Culture of India",
    "Average": "Average",
    "Biology - Agriculture": "Biology - Nutrition in Plants & Animals",
    "Biology - Cell Biology": "Biology - Cell Structure & Functions",
    "Biology - Ecology": "Biology - Ecology & Environment",
    "Biology - Human Body": "Biology - Human Digestive System",
    "Biology - Plant Physiology": "Biology - Photosynthesis",
    "Biology - Reproduction": "Biology - Cell Structure & Functions",
    "Biology - Tissues": "Biology - Cell Structure & Functions",
    "Blood Relations": "Blood Relations",
    "Chemistry - Acids Bases and Salts": "Chemistry - Acids, Bases & Salts",
    "Chemistry - Atoms and Molecules": "Chemistry - Atoms & Molecules",
    "Chemistry - Carbon and Compounds": "Chemistry - Carbon & Its Compounds",
    "Chemistry - Chemical Reactions": "Chemistry - Chemical Reactions & Types",
    "Chemistry - Metals and Non-metals": "Chemistry - Metals & Non-Metals",
    "Chemistry - Mixtures and Solutions": "Chemistry - Elements, Compounds & Mixtures",
    "Coding-Decoding": "Coding & Decoding - Letter Coding",
    "Compound Interest": "Compound Interest",
    "Current Affairs": "Current Events - National",
    "Direction Sense": "Direction & Distance",
    "Economy and Schemes": "Government Schemes",
    "General Awareness - Miscellaneous": "Famous Personalities",
    "General Science - Miscellaneous": "Physics - Scientific Instruments",
    "Geometry": "Geometry - Lines, Angles & Triangles",
    "Indian Geography": "Indian Geography - Physical Features",
    "Indian History": "Indian History - Key Events",
    "Indian Polity": "Indian Polity - Constitution Basics",
    "Mathematical Operations": "Mathematical Operations",
    "Mensuration": "Mensuration 3D - Volume & Surface Area",
    "Number Series": "Number Series - Missing Term",
    "Number System": "Number System",
    "Percentage": "Percentage",
    "Physics - Electricity and Magnetism": "Physics - Electricity - Current, Voltage, Resistance",
    "Physics - Fluids": "Physics - Pressure",
    "Physics - Gravitation": "Physics - Gravitation",
    "Physics - Light": "Physics - Light - Refraction",
    "Physics - Motion": "Physics - Motion: Speed, Velocity, Distance",
    "Physics - Sound": "Physics - Sound - Properties",
    "Profit and Loss": "Profit & Loss",
    "Puzzle Arrangement": "Puzzle - Basic",
    "Ratio and Proportion": "Ratio & Proportion",
    "Science and Technology": "Science & Technology News",
    "Seating/Ranking Arrangement": "Ranking & Order",
    "Simple Interest": "Simple Interest",
    "Speed Time and Distance": "Time, Speed & Distance",
    "Sports": "Sports - National & International",
    "Statistics": "Data Interpretation - Table",
    "Time and Work": "Time & Work",
    "Trigonometry": "Trigonometry - Basic Ratios & Identities",
}


def parse_year_shift(source_pdf: str) -> tuple[int | None, str | None]:
    match = re.search(r"(\d{2})-(\d{2})-(\d{4})-S(\d+)", source_pdf or "", re.IGNORECASE)
    if not match:
        return None, None
    day, month, year, shift = match.groups()
    return int(year), f"Shift {shift}"


def app_id(question: dict) -> str:
    raw_id = question["id"].replace("_", "-")
    return raw_id


def clean_app_text(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+['\"]$", "", text)
    return text


def convert_question(question: dict) -> dict:
    source_pdf = question.get("source_metadata", {}).get("source_pdf")
    year, shift = parse_year_shift(source_pdf)
    original_topic = question["topic"]
    return {
        "id": app_id(question),
        "exam": "RRB Technician Grade 3",
        "year": year,
        "shift": shift,
        "subject": question["subject"],
        "topic": TOPIC_TO_APP.get(original_topic, original_topic),
        "question": clean_app_text(question["question"]),
        "options": [clean_app_text(option) for option in question["options"]],
        "answer": question["answer"],
        "source": source_pdf,
        "is_official": True,
        "difficulty": DIFFICULTY_TO_APP.get(question.get("difficulty"), "medium"),
        "source_metadata": {
            "source_layer": SOURCE_FILE.name,
            "source_pdf": source_pdf,
            "source_question_number": question.get("source_metadata", {}).get("question_number"),
            "source_question_id": question["id"],
            "original_topic": original_topic,
            "answer_label": question.get("answer_label"),
            "answer_recovery": question.get("source_metadata", {}).get("answer_recovery"),
            "topic_tagging": question.get("topic_tagging"),
            "difficulty_tagging": question.get("difficulty_tagging"),
            "original_difficulty": question.get("difficulty"),
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_payload = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    existing_bank = json.loads(FRONTEND_BANK.read_text(encoding="utf-8"))
    app_questions = [convert_question(question) for question in source_payload.get("questions", [])]

    existing_ids = {question.get("id") for question in existing_bank}
    incoming_ids = {question.get("id") for question in app_questions}
    id_collisions = sorted(existing_ids & incoming_ids)
    duplicate_incoming_ids = [
        question_id
        for question_id, count in Counter(question.get("id") for question in app_questions).items()
        if count > 1
    ]

    app_questions.sort(key=lambda item: (item["year"] or 0, item["shift"] or "", item["subject"], item["topic"], item["id"]))
    existing_without_replaced = [
        question for question in existing_bank if question.get("id") not in incoming_ids
    ]
    merged_preview = [*existing_without_replaced, *app_questions]

    APP_MERGE_OUT.write_text(json.dumps(app_questions, ensure_ascii=False, indent=2), encoding="utf-8")
    MERGED_PREVIEW_OUT.write_text(json.dumps(merged_preview, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "exam": "RRB Technician Grade 3",
        "language": "English",
        "source_file": SOURCE_FILE.name,
        "frontend_bank_file": str(FRONTEND_BANK.relative_to(PROJECT_ROOT)),
        "existing_frontend_questions": len(existing_bank),
        "existing_questions_replaced_by_id": len(id_collisions),
        "app_merge_questions": len(app_questions),
        "merged_preview_questions": len(merged_preview),
        "id_collisions_with_existing_bank": id_collisions,
        "duplicate_incoming_ids": duplicate_incoming_ids,
        "difficulty_mapping": DIFFICULTY_TO_APP,
        "topic_mapping_applied": True,
        "by_subject": dict(sorted(Counter(question["subject"] for question in app_questions).items())),
        "by_difficulty": dict(sorted(Counter(question["difficulty"] for question in app_questions).items())),
        "output_files": [
            APP_MERGE_OUT.name,
            MERGED_PREVIEW_OUT.name,
            SUMMARY_OUT.name,
        ],
        "notes": [
            "The live frontend/data/question-bank.json file was not overwritten.",
            "Use the merged preview for validation before replacing or extending the live frontend bank.",
            "If the live bank already contains these Technician IDs, the preview replaces them instead of appending duplicates.",
            "App difficulty values are mapped from basic/intermediate/advanced to easy/medium/hard.",
        ],
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
