import json
from copy import deepcopy
from pathlib import Path


BASE = Path(r"C:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
PARSED_DIR = BASE / "parsed-json" / "technician-grade-3"
OUT_DIR = BASE / "quality-gated-json" / "technician-grade-3"
SUMMARY_PATH = BASE / "quality-gated-json" / "technician-grade-3-quality-gated-summary.json"
AUDIT_PATH = BASE / "quality-gated-json" / "technician-grade-3-excluded-blank-option-audit.json"

BLANK_OPTIONS = {"A.", "B.", "C.", "D.", "1.", "2.", "3.", "4."}
REPLACEMENT_CHAR = "\ufffd"


def has_blank_option(question: dict) -> bool:
    return any(option.strip() in BLANK_OPTIONS for option in question.get("options", []))


def has_replacement_char(question: dict) -> bool:
    combined = " ".join([question.get("question", ""), *question.get("options", [])])
    return REPLACEMENT_CHAR in combined


def mark_question(question: dict, paper_name: str) -> tuple[dict, dict | None]:
    updated = deepcopy(question)
    if not has_blank_option(updated):
        updated.setdefault("exclude_from_bank", False)
        return updated, None

    flags = set(updated.get("normalization_flags", []))
    flags.add("blank_option_text")
    flags.add("exclude_from_bank")
    flags.add("needs_visual_option_recovery")
    updated["normalization_flags"] = sorted(flags)
    updated["exclude_from_bank"] = True
    updated["exclusion_reason"] = "blank_option_text"

    audit = {
        "paper": paper_name,
        "source_pdf": updated.get("source_pdf"),
        "source_txt": updated.get("source_txt"),
        "section": updated.get("section"),
        "question_number": updated.get("question_number"),
        "question": updated.get("question"),
        "options": updated.get("options", []),
        "reason": "A-D options are blank after direct English text extraction; visual recovery required before bank use.",
    }
    return updated, audit


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audits = []
    paper_summaries = []

    for src in sorted(PARSED_DIR.glob("*.parsed.json")):
        if src.name == "technician-grade-3-parse-summary.json":
            continue

        data = json.loads(src.read_text(encoding="utf-8"))
        output = deepcopy(data)
        updated_questions = []
        paper_excluded = 0

        for question in data.get("questions", []):
            updated, audit = mark_question(question, src.name)
            updated_questions.append(updated)
            if audit:
                audits.append(audit)
                paper_excluded += 1

        output["questions"] = updated_questions
        notes = output.get("notes", [])
        notes.append(
            "Quality gate applied: blank-option questions are retained for traceability but excluded from bank use until visual option recovery."
        )
        output["notes"] = notes

        out_path = OUT_DIR / src.name.replace(".parsed.json", ".quality-gated.json")
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

        active_questions = [question for question in updated_questions if not question.get("exclude_from_bank")]
        paper_summaries.append(
            {
                "paper": out_path.name,
                "questions": len(updated_questions),
                "usable_questions": len(active_questions),
                "excluded_blank_option_questions": paper_excluded,
                "active_blank_option_questions": sum(1 for question in active_questions if has_blank_option(question)),
                "replacement_char_questions": sum(1 for question in updated_questions if has_replacement_char(question)),
                "sections": output.get("sections", {}),
            }
        )

    summary = {
        "layer": "technician-grade-3-quality-gated",
        "language_policy": "English source papers only; no Hindi OCR/translation for bank use.",
        "paper_count": len(paper_summaries),
        "total_questions_retained": sum(paper["questions"] for paper in paper_summaries),
        "total_usable_questions": sum(paper["usable_questions"] for paper in paper_summaries),
        "total_excluded_blank_option_questions": sum(paper["excluded_blank_option_questions"] for paper in paper_summaries),
        "total_active_blank_option_questions": sum(paper["active_blank_option_questions"] for paper in paper_summaries),
        "total_replacement_char_questions": sum(paper["replacement_char_questions"] for paper in paper_summaries),
        "audit_file": AUDIT_PATH.name,
        "papers": paper_summaries,
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps(audits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
