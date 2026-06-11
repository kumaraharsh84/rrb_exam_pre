import json
import re
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parent
SOURCE_DIR = BASE / "answer-recovered-json" / "technician-grade-3"
OUT_DIR = BASE / "bank-ready-json" / "technician-grade-3"
COMBINED_OUT = OUT_DIR / "technician-grade-3-2026-bank-ready.json"
SUMMARY_OUT = OUT_DIR / "technician-grade-3-2026-bank-ready-summary.json"

ANSWER_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
OPTION_LABEL_RE = re.compile(r"^\s*([A-D])[\.)]\s*", re.IGNORECASE)

MOJIBAKE_REPLACEMENTS = {
    "â‚¹": "\u20b9",
    "Â°": "\u00b0",
    "Â": "",
    "â€“": "-",
    "â€”": "-",
    "â€˜": "'",
    "â€™": "'",
    "â€œ": '"',
    "â€": '"',
    "â€¦": "...",
    "Ã—": "x",
    "Ã·": "/",
}


def clean_text(value):
    if value is None:
        return None
    text = str(value)
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_option(option: str, index: int) -> str:
    text = clean_text(option)
    text = OPTION_LABEL_RE.sub("", text).strip()
    label = chr(ord("A") + index)
    return f"{label}) {text}"


def source_files() -> list[Path]:
    return sorted(
        path
        for path in SOURCE_DIR.glob("*.answer-recovered.json")
        if not path.name.endswith(".answer-recovery-summary.json")
    )


def make_bank_id(question: dict) -> str:
    paper = question["paper"].lower()
    paper = paper.replace("rrb-technician-iii-questions-paper-english-", "")
    paper = re.sub(r"[^a-z0-9]+", "_", paper).strip("_")
    return f"rrb_technician_grade_3_{paper}_q{question['question_number']:03d}"


def invalid_question_reason(question: dict) -> str | None:
    if question.get("exclude_from_bank"):
        return "excluded_from_source"
    question_text = clean_text(question.get("question"))
    if not question_text or not re.search(r"[A-Za-z]", question_text):
        return "missing_or_non_text_question"
    answer_letter = question.get("answer")
    if answer_letter not in ANSWER_INDEX:
        return "missing_answer"
    options = question.get("options") or []
    if len(options) != 4:
        return "invalid_option_count"
    if any(OPTION_LABEL_RE.sub("", option).strip() in {"", "-"} for option in options):
        return "blank_option_text"
    return None


def convert_question(question: dict) -> dict | None:
    if invalid_question_reason(question):
        return None

    answer_letter = question.get("answer")
    options = question.get("options") or []
    cleaned_options = [clean_option(option, index) for index, option in enumerate(options)]

    return {
        "id": make_bank_id(question),
        "exam": "RRB Technician Grade 3",
        "language": "English",
        "subject": clean_text(question.get("section")),
        "topic": None,
        "difficulty": None,
        "question": clean_text(question.get("question")),
        "options": cleaned_options,
        "answer": ANSWER_INDEX[answer_letter],
        "answer_label": answer_letter,
        "correct_option": clean_option(question.get("correct_option") or options[ANSWER_INDEX[answer_letter]], ANSWER_INDEX[answer_letter]),
        "explanation": clean_text(question.get("explanation")),
        "source_type": "official_exam_pdf",
        "source_name": clean_text(question.get("source_pdf")),
        "source_url": None,
        "verified": True,
        "verification_method": "visual_answer_highlight_recovery",
        "source_metadata": {
            "paper": clean_text(question.get("paper")),
            "source_pdf": clean_text(question.get("source_pdf")),
            "source_txt": clean_text(question.get("source_txt")),
            "question_number": question.get("question_number"),
            "answer_recovery": question.get("answer_recovery"),
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bank_questions = []
    skipped = Counter()
    paper_counts = Counter()
    subject_counts = Counter()

    for path in source_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        for question in data.get("questions", []):
            converted = convert_question(question)
            if converted is None:
                skipped[invalid_question_reason(question) or "invalid_question"] += 1
                continue
            bank_questions.append(converted)
            paper_counts[converted["source_metadata"]["source_pdf"]] += 1
            subject_counts[converted["subject"]] += 1

    bank_questions.sort(key=lambda item: (item["source_metadata"]["source_pdf"], item["source_metadata"]["question_number"]))

    payload = {
        "exam": "RRB Technician Grade 3",
        "language": "English",
        "source_scope": "2026 English Technician Grade 3 papers",
        "question_count": len(bank_questions),
        "questions": bank_questions,
    }
    COMBINED_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for subject in sorted(subject_counts):
        subject_slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
        subject_questions = [question for question in bank_questions if question["subject"] == subject]
        subject_payload = {
            "exam": "RRB Technician Grade 3",
            "language": "English",
            "subject": subject,
            "question_count": len(subject_questions),
            "questions": subject_questions,
        }
        (OUT_DIR / f"technician-grade-3-2026-{subject_slug}.bank-ready.json").write_text(
            json.dumps(subject_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    summary = {
        "exam": "RRB Technician Grade 3",
        "language": "English",
        "source_scope": "2026 English Technician Grade 3 papers",
        "input_files": len(source_files()),
        "bank_ready_questions": len(bank_questions),
        "skipped_questions": dict(skipped),
        "by_subject": dict(sorted(subject_counts.items())),
        "by_paper": dict(sorted(paper_counts.items())),
        "output_files": [
            COMBINED_OUT.name,
            *[
                f"technician-grade-3-2026-{re.sub(r'[^a-z0-9]+', '-', subject.lower()).strip('-')}.bank-ready.json"
                for subject in sorted(subject_counts)
            ],
            SUMMARY_OUT.name,
        ],
        "notes": [
            "Only non-excluded questions are included.",
            "Answer is 0-indexed for app/question-bank use.",
            "Topic and difficulty are intentionally null until the tagging phase.",
            "Common extraction mojibake is normalized in bank-ready text.",
        ],
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
