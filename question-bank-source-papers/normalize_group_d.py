import json
import re
from pathlib import Path

BASE = Path(r"C:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
SRC_DIR = BASE / "ocr-recovered-json" / "group-d"
OUT_DIR = BASE / "normalized-json" / "group-d"
SUMMARY_PATH = BASE / "normalized-json" / "group-d-normalization-summary.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MOJIBAKE_MARKERS = ["â", "à°", "à±", "Ã", "Î", "�"]
PLACEHOLDER = "[UNEXTRACTED_MATH_OR_IMAGE_CONTENT]"
WEIRD_CONTROL_RE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]")
MULTISPACE_RE = re.compile(r"\s+")


def cleanup_controls(text: str) -> str:
    text = WEIRD_CONTROL_RE.sub("", text)
    return MULTISPACE_RE.sub(" ", text).strip()


def maybe_repair_mojibake(text: str):
    if not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text, False

    candidates = []
    for enc in ("cp1252", "latin1"):
        try:
            repaired = text.encode(enc, errors="strict").decode("utf-8", errors="strict")
            candidates.append(repaired)
        except Exception:
            pass

    def score(value: str):
        bad = sum(value.count(m) for m in MOJIBAKE_MARKERS)
        repl = value.count("?")
        return (bad, repl, -len(value))

    if not candidates:
        return text, False

    best = min(candidates, key=score)
    return best, best != text


def normalize_text(text: str):
    text = cleanup_controls(text)
    repaired, changed = maybe_repair_mojibake(text)
    repaired = cleanup_controls(repaired)
    replacements = {
        "`": "'",
        "â€“": "-",
        "â€”": "-",
        "â€˜": "'",
        "â€™": "'",
        'â€œ': '"',
        'â€': '"',
        "âˆ’": "-",
        "â‚¹": "₹",
        "Î©": "Ω"
    }
    normalized = repaired
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    normalized = cleanup_controls(normalized)
    return normalized, changed or normalized != text


def classify_flags(question_text: str, options):
    flags = []
    if PLACEHOLDER in question_text:
        flags.append("missing_stem_or_image")
    if any(opt in {"A.", "B.", "C.", "D."} for opt in options):
        flags.append("blank_option_text")
    if any(ord(ch) > 127 for ch in question_text):
        flags.append("non_ascii_text")
    return flags


summary = {
    "paper_count": 0,
    "total_questions": 0,
    "total_repaired_strings": 0,
    "total_placeholder_questions": 0,
    "total_blank_option_questions": 0,
    "papers": []
}

for src in sorted(SRC_DIR.glob("*.parsed.json")):
    data = json.loads(src.read_text(encoding="utf-8"))
    repaired_strings = 0
    placeholder_questions = 0
    blank_option_questions = 0

    for question in data.get("questions", []):
        q_text, changed = normalize_text(question.get("question", ""))
        question["question"] = q_text
        if changed:
            repaired_strings += 1

        new_options = []
        for opt in question.get("options", []):
            fixed_opt, opt_changed = normalize_text(opt)
            new_options.append(fixed_opt)
            if opt_changed:
                repaired_strings += 1
        question["options"] = new_options

        flags = classify_flags(question["question"], question["options"])
        if flags:
            question["normalization_flags"] = flags
        if "missing_stem_or_image" in flags:
            placeholder_questions += 1
        if "blank_option_text" in flags:
            blank_option_questions += 1

    notes = data.get("notes", [])
    notes.append("Normalization pass applied: controls cleaned, common mojibake repaired, flags added for missing/image-heavy stems.")
    data["notes"] = notes
    data["normalization_summary"] = {
        "repaired_strings": repaired_strings,
        "placeholder_questions": placeholder_questions,
        "blank_option_questions": blank_option_questions
    }

    out = OUT_DIR / src.name.replace('.parsed.json', '.normalized.json')
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    summary["paper_count"] += 1
    summary["total_questions"] += data.get("question_count", 0)
    summary["total_repaired_strings"] += repaired_strings
    summary["total_placeholder_questions"] += placeholder_questions
    summary["total_blank_option_questions"] += blank_option_questions
    summary["papers"].append({
        "paper": src.name,
        "questions": data.get("question_count", 0),
        "repaired_strings": repaired_strings,
        "placeholder_questions": placeholder_questions,
        "blank_option_questions": blank_option_questions
    })

SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
