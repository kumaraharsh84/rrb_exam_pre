import json
import re
import subprocess
from pathlib import Path


BASE = Path(r"C:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
PDF_DIR = BASE / "ntpc"
TXT_DIR = BASE / "extracted-text" / "ntpc"
OUT_DIR = BASE / "parsed-json" / "ntpc"
SUMMARY_PATH = OUT_DIR / "ntpc-parse-summary.json"
PDFTOTEXT = Path(
    r"C:\Users\kumar\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftotext.exe"
)

SECTION_LINE_RE = re.compile(r"^\s*Section\s*:\s*(.+?)\s*$", re.IGNORECASE)
QUESTION_RE = re.compile(r"^\s*Q\.(\d+)\s*(.*)$")
OPTION_RE = re.compile(r"^\s*(?:Ans\s*)?([A-D1-4])\.\s*(.*)$", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
SKIP_PREFIXES = (
    "Question Type",
    "Question ID",
    "Option A ID",
    "Option B ID",
    "Option C ID",
    "Option D ID",
    "Status",
    "Chosen Option",
)


def clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value.strip())


def extract_pdf(pdf_path: Path) -> Path:
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = TXT_DIR / f"{pdf_path.stem}.txt"
    subprocess.run([str(PDFTOTEXT), "-layout", str(pdf_path), str(txt_path)], check=True)
    return txt_path


def flush_question(questions: list[dict], paper_name: str, source_pdf: Path, source_txt: Path, current: dict | None) -> None:
    if current is None:
        return

    labels = ("1", "2", "3", "4") if any(label in current["options"] for label in ("1", "2", "3", "4")) else ("A", "B", "C", "D")
    options = []
    for label in labels:
        body = current["options"].get(label, "").strip()
        options.append(clean_text(f"{label}. {body}".strip()))

    questions.append(
        {
            "paper": paper_name,
            "section": current["section"],
            "question_number": current["question_number"],
            "question": clean_text(current["question"]),
            "options": options,
            "source_pdf": source_pdf.name,
            "source_txt": source_txt.name,
            "answer": None,
            "explanation": None,
        }
    )


def parse_text(txt_path: Path) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paper_name = txt_path.stem
    source_pdf = PDF_DIR / f"{paper_name}.pdf"
    questions = []
    current_section = None
    current = None
    current_option = None

    for raw_line in txt_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        section_match = SECTION_LINE_RE.match(line)
        if section_match:
            flush_question(questions, paper_name, source_pdf, txt_path, current)
            current_section = clean_text(section_match.group(1))
            current = None
            current_option = None
            continue

        question_match = QUESTION_RE.match(line)
        if question_match and current_section:
            flush_question(questions, paper_name, source_pdf, txt_path, current)
            current = {
                "section": current_section,
                "question_number": int(question_match.group(1)),
                "question": question_match.group(2).strip(),
                "options": {},
            }
            current_option = None
            continue

        if current is None:
            continue

        if any(line.startswith(prefix) for prefix in SKIP_PREFIXES):
            continue

        option_match = OPTION_RE.match(line)
        if option_match:
            current_option = option_match.group(1).upper()
            current["options"][current_option] = option_match.group(2).strip()
            continue

        if current_option is not None:
            current["options"][current_option] = f"{current['options'].get(current_option, '')} {line}".strip()
        else:
            current["question"] = f"{current['question']} {line}".strip()

    flush_question(questions, paper_name, source_pdf, txt_path, current)

    sections = {}
    incomplete = 0
    for question in questions:
        sections[question["section"]] = sections.get(question["section"], 0) + 1
        if any(option in {"A.", "B.", "C.", "D.", "1.", "2.", "3.", "4."} for option in question["options"]):
            incomplete += 1

    data = {
        "paper": txt_path.name,
        "question_count": len(questions),
        "sections": sections,
        "answer_key_present": False,
        "notes": [
            "Direct text extraction is English and text-based for this paper.",
            "NTPC options use A-D labels.",
            "Correct-answer highlighting did not survive plain-text extraction.",
            "answer is null for every question until answer-key recovery is handled.",
        ],
        "questions": questions,
    }

    out_path = OUT_DIR / f"{paper_name}.parsed.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "paper": source_pdf.name,
        "question_count": len(questions),
        "sections": sections,
        "incomplete_questions": incomplete,
        "parsed_json": out_path.name,
        "source_txt": txt_path.name,
    }


def parse_one(pdf_name: str) -> dict:
    txt_path = extract_pdf(PDF_DIR / pdf_name)
    return parse_text(txt_path)


def main() -> None:
    results = []
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        
        results.append(parse_one(pdf_path.name))

    summary = {
        "paper_count": len(results),
        "total_questions": sum(result["question_count"] for result in results),
        "total_incomplete_questions": sum(result["incomplete_questions"] for result in results),
        "language_policy": "English source papers only; no Hindi OCR/translation for bank use.",
        "papers": results,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
