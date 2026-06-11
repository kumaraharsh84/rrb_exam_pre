import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path

from PIL import Image


BASE = Path(r"C:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
PDF_PATH = BASE / "technician-grade-3" / "RRB-Technician-III-Questions-Paper-English-06-03-2026-S1.pdf"
SOURCE_JSON = BASE / "quality-gated-json" / "technician-grade-3" / "RRB-Technician-III-Questions-Paper-English-06-03-2026-S1.quality-gated.json"
OUT_DIR = BASE / "answer-recovered-json" / "technician-grade-3"
WORK_DIR = BASE / "answer-recovery-tests" / "technician-grade-3" / "s1-answer-recovery"
PAGE_IMG_DIR = WORK_DIR / "pages"
PAGE_TEXT_DIR = WORK_DIR / "page-text"
OUT_PATH = OUT_DIR / "RRB-Technician-III-Questions-Paper-English-06-03-2026-S1.answer-recovered.json"
SUMMARY_PATH = OUT_DIR / "RRB-Technician-III-Questions-Paper-English-06-03-2026-S1.answer-recovery-summary.json"

PDFTOPPM = Path(
    r"C:\Users\kumar\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftoppm.exe"
)
PDFTOTEXT = Path(
    r"C:\Users\kumar\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftotext.exe"
)

QUESTION_RE = re.compile(r"(?m)^\s*Q\.(\d+)")
LABELS = ("A", "B", "C", "D")


def render_pages() -> None:
    PAGE_IMG_DIR.mkdir(parents=True, exist_ok=True)
    if len(list(PAGE_IMG_DIR.glob("*.png"))) >= 17:
        return
    subprocess.run(
        [
            str(PDFTOPPM),
            "-f",
            "1",
            "-l",
            "17",
            "-r",
            "220",
            "-png",
            str(PDF_PATH),
            str(PAGE_IMG_DIR / "page"),
        ],
        check=True,
    )


def extract_page_text() -> None:
    PAGE_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    for page in range(1, 18):
        out_path = PAGE_TEXT_DIR / f"page-{page:02d}.txt"
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
                str(PDF_PATH),
                str(out_path),
            ],
            check=True,
        )


def page_questions(page: int) -> list[int]:
    text = (PAGE_TEXT_DIR / f"page-{page:02d}.txt").read_text(encoding="utf-8", errors="replace")
    return [int(value) for value in QUESTION_RE.findall(text)]


def colored_option_rows(image_path: Path, page: int) -> list[dict]:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    rows = {}

    # The option marks/text live in the left content column. This avoids most logos and watermarks.
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

        # Page 1 has large red app/header art above the first question.
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


def recover_answers() -> tuple[dict[int, dict], list[dict]]:
    answers = {}
    page_reports = []

    for page in range(1, 18):
        questions = page_questions(page)
        if not questions:
            page_reports.append({"page": page, "questions": [], "status": "no_questions"})
            continue

        image_path = PAGE_IMG_DIR / f"page-{page:02d}.png"
        rows = colored_option_rows(image_path, page)
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_pages()
    extract_page_text()
    recovered_answers, page_reports = recover_answers()

    data = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    output = deepcopy(data)
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
    output["notes"] = notes
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    usable_questions = [question for question in output.get("questions", []) if not question.get("exclude_from_bank")]
    summary = {
        "paper": PDF_PATH.name,
        "source_json": SOURCE_JSON.name,
        "output_json": OUT_PATH.name,
        "question_count": len(output.get("questions", [])),
        "usable_questions": len(usable_questions),
        "questions_with_recovered_answers": questions_with_answers,
        "usable_questions_with_recovered_answers": usable_questions_with_answers,
        "usable_questions_still_missing_answers": sum(1 for question in usable_questions if question.get("answer") is None),
        "page_reports": page_reports,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
