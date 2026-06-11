import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path

from PIL import Image


BASE = Path(r"C:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
PDF_DIR = BASE / "group d"
SOURCE_DIR = BASE / "quality-gated-json" / "group-d"
OUT_DIR = BASE / "answer-recovered-json" / "group-d"
WORK_ROOT = BASE / "answer-recovery-tests" / "group-d"
SUMMARY_PATH = OUT_DIR / "group-d-answer-recovery-summary.json"

PDFTOPPM = Path(
    r"C:\Users\kumar\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftoppm.exe"
)
PDFTOTEXT = Path(
    r"C:\Users\kumar\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftotext.exe"
)

QUESTION_RE = re.compile(r"(?m)^\s*Q\.(\d+)")
LABELS = ("A", "B", "C", "D")

MANUAL_VISUAL_ANSWER_FIXES = {
    "RRB-Group-D-CBT-1-Paper_9-2-2026_S1": {
        27: "B",
        28: "D",
        29: "B",
        30: "B",
        31: "A",
        32: "D",
        33: "D",
    }
}


def pdf_page_count(pdf_path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True)
    match = re.search(r"^Pages:\s*(\d+)", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not read page count for {pdf_path}")
    return int(match.group(1))


def target_pdfs() -> list[Path]:
    return sorted(PDF_DIR.glob("*.pdf"))


def render_pages(pdf_path: Path, page_count: int, page_img_dir: Path) -> None:
    page_img_dir.mkdir(parents=True, exist_ok=True)
    if len(list(page_img_dir.glob("*.png"))) >= page_count:
        return
    subprocess.run(
        [
            str(PDFTOPPM),
            "-f",
            "1",
            "-l",
            str(page_count),
            "-r",
            "220",
            "-png",
            str(pdf_path),
            str(page_img_dir / "page"),
        ],
        check=True,
    )


def extract_page_text(pdf_path: Path, page_count: int, page_text_dir: Path) -> None:
    page_text_dir.mkdir(parents=True, exist_ok=True)
    for page in range(1, page_count + 1):
        out_path = page_text_dir / f"page-{page:02d}.txt"
        if out_path.exists():
            continue
        subprocess.run(
            [
                str(PDFTOTEXT),
                "-f",
                str(page),
                "-l",
                str(page),
                "-layout",
                str(pdf_path),
                str(out_path),
            ],
            check=True,
        )


def page_questions(page: int, page_text_dir: Path) -> list[int]:
    text = (page_text_dir / f"page-{page:02d}.txt").read_text(encoding="utf-8", errors="replace")
    return [int(value) for value in QUESTION_RE.findall(text)]


def colored_option_rows(image_path: Path, page: int) -> list[dict]:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    rows = {}

    for y in range(height):
        red_count = 0
        green_count = 0
        for x in range(80, min(width, 900)):
            red, green, blue = image.getpixel((x, y))
            if green > 120 and red < 120 and blue < 120:
                green_count += 1
            elif red > 150 and green < 110 and blue < 110:
                red_count += 1
        if red_count + green_count > 8:
            rows[y] = {"red": red_count, "green": green_count}

    groups = []
    current = []
    last_y = None
    for y in sorted(rows):
        if last_y is None or y - last_y <= 12:
            current.append(y)
        else:
            groups.append(current)
            current = [y]
        last_y = y
    if current:
        groups.append(current)

    raw_clusters = []
    for y_group in groups:
        y_center = sum(y_group) // len(y_group)
        red_count = sum(rows[y]["red"] for y in y_group)
        green_count = sum(rows[y]["green"] for y in y_group)
        if page == 1 and y_center < 900:
            continue
        if red_count + green_count > 5000:
            continue
        raw_clusters.append(
            {
                "y": y_center,
                "red_pixels": red_count,
                "green_pixels": green_count,
                "is_green": green_count > red_count,
            }
        )

    clusters = []
    for cluster in raw_clusters:
        if (
            clusters
            and cluster["y"] - clusters[-1]["y"] <= 45
            and cluster["is_green"] == clusters[-1]["is_green"]
        ):
            clusters[-1]["red_pixels"] += cluster["red_pixels"]
            clusters[-1]["green_pixels"] += cluster["green_pixels"]
            continue
        clusters.append(cluster)
    return clusters


def recover_answers_for_pdf(pdf_path: Path, page_count: int, page_img_dir: Path, page_text_dir: Path) -> tuple[dict[int, dict], list[dict]]:
    answers = {}
    page_reports = []
    for page in range(1, page_count + 1):
        questions = page_questions(page, page_text_dir)
        if not questions:
            page_reports.append({"page": page, "questions": [], "status": "no_questions"})
            continue

        rows = colored_option_rows(page_img_dir / f"page-{page:02d}.png", page)
        expected_rows = len(questions) * 4
        if len(rows) != expected_rows:
            page_reports.append(
                {
                    "page": page,
                    "questions": questions,
                    "status": "row_count_mismatch",
                    "expected_option_rows": expected_rows,
                    "detected_option_rows": len(rows),
                }
            )
            continue

        page_ok = True
        for index, question_number in enumerate(questions):
            option_rows = rows[index * 4 : (index + 1) * 4]
            green_indexes = [idx for idx, row in enumerate(option_rows) if row["is_green"]]
            if len(green_indexes) != 1:
                page_ok = False
                continue
            answer_index = green_indexes[0]
            answers[question_number] = {
                "answer": LABELS[answer_index],
                "answer_recovery": {
                    "method": "visual_green_option_row_detection",
                    "page": page,
                    "option_row_y": option_rows[answer_index]["y"],
                },
            }

        page_reports.append(
            {
                "page": page,
                "questions": questions,
                "status": "ok" if page_ok else "green_detection_issue",
                "detected_option_rows": len(rows),
            }
        )
    return answers, page_reports


def apply_answers(pdf_path: Path, recovered_answers: dict[int, dict], page_reports: list[dict]) -> dict:
    source_json = SOURCE_DIR / f"{pdf_path.stem}.quality-gated.json"
    data = json.loads(source_json.read_text(encoding="utf-8"))
    output = deepcopy(data)
    manual_fixes = MANUAL_VISUAL_ANSWER_FIXES.get(pdf_path.stem, {})
    for question_number, answer in manual_fixes.items():
        recovered_answers[question_number] = {
            "answer": answer,
            "answer_recovery": {
                "method": "manual_visual_review",
                "note": "Applied after visual inspection of a page where automatic option-row counting mismatched.",
            },
        }

    questions_with_answers = 0
    usable_questions_with_answers = 0

    for question in output.get("questions", []):
        recovered = recovered_answers.get(question.get("question_number"))
        if not recovered:
            continue
        question["answer"] = recovered["answer"]
        question["correct_option"] = next(
            (option for option in question.get("options", []) if option.startswith(f"{recovered['answer']}.")),
            None,
        )
        question["answer_recovery"] = recovered["answer_recovery"]
        questions_with_answers += 1
        if not question.get("exclude_from_bank"):
            usable_questions_with_answers += 1

    notes = output.get("notes", [])
    notes.append("Answer recovery applied using visual green option row detection on rendered PDF pages.")
    if manual_fixes:
        notes.append("Manual visual answer fixes were applied for row-count mismatch pages.")
    output["notes"] = notes

    out_path = OUT_DIR / f"{pdf_path.stem}.answer-recovered.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    usable_questions = [question for question in output.get("questions", []) if not question.get("exclude_from_bank")]
    paper_summary = {
        "paper": pdf_path.name,
        "source_json": source_json.name,
        "output_json": out_path.name,
        "question_count": len(output.get("questions", [])),
        "usable_questions": len(usable_questions),
        "questions_with_recovered_answers": questions_with_answers,
        "usable_questions_with_recovered_answers": usable_questions_with_answers,
        "usable_questions_still_missing_answers": sum(1 for question in usable_questions if question.get("answer") is None),
        "manual_visual_answer_fixes": len(manual_fixes),
        "page_reports": page_reports,
    }

    paper_summary_path = OUT_DIR / f"{pdf_path.stem}.answer-recovery-summary.json"
    paper_summary_path.write_text(json.dumps(paper_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return paper_summary


def process_pdf(pdf_path: Path) -> dict:
    page_count = pdf_page_count(pdf_path)
    work_dir = WORK_ROOT / pdf_path.stem
    page_img_dir = work_dir / "pages"
    page_text_dir = work_dir / "page-text"
    render_pages(pdf_path, page_count, page_img_dir)
    extract_page_text(pdf_path, page_count, page_text_dir)
    recovered_answers, page_reports = recover_answers_for_pdf(pdf_path, page_count, page_img_dir, page_text_dir)
    return apply_answers(pdf_path, recovered_answers, page_reports)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paper_summaries = [process_pdf(pdf_path) for pdf_path in target_pdfs()]
    summary = {
        "scope": "Group D papers",
        "paper_count": len(paper_summaries),
        "total_questions": sum(paper["question_count"] for paper in paper_summaries),
        "total_usable_questions": sum(paper["usable_questions"] for paper in paper_summaries),
        "total_questions_with_recovered_answers": sum(paper["questions_with_recovered_answers"] for paper in paper_summaries),
        "total_usable_questions_with_recovered_answers": sum(paper["usable_questions_with_recovered_answers"] for paper in paper_summaries),
        "total_usable_questions_still_missing_answers": sum(paper["usable_questions_still_missing_answers"] for paper in paper_summaries),
        "papers": paper_summaries,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
