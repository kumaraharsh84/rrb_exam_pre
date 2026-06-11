import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path


BASE = Path(__file__).resolve().parent
SOURCE_DIR = BASE / "topic-tagged-json" / "technician-grade-3"
OUT_DIR = BASE / "difficulty-tagged-json" / "technician-grade-3"
SOURCE_FILE = SOURCE_DIR / "technician-grade-3-2026-topic-tagged.json"
COMBINED_OUT = OUT_DIR / "technician-grade-3-2026-difficulty-tagged.json"
SUMMARY_OUT = OUT_DIR / "technician-grade-3-2026-difficulty-tagging-summary.json"


BASIC_TOPICS = {
    "Art and Culture",
    "Biology - Agriculture",
    "Biology - Cell Biology",
    "Biology - Ecology",
    "Biology - Human Body",
    "Biology - Plant Physiology",
    "Biology - Reproduction",
    "Biology - Tissues",
    "Chemistry - Metals and Non-metals",
    "Chemistry - Mixtures and Solutions",
    "Current Affairs",
    "Economy and Schemes",
    "Indian Geography",
    "Indian History",
    "Indian Polity",
    "Physics - Sound",
    "Science and Technology",
    "Sports",
}

INTERMEDIATE_TOPICS = {
    "Age Problems",
    "Algebra",
    "Alphabet Series",
    "Analogy",
    "Average",
    "Blood Relations",
    "Chemistry - Acids Bases and Salts",
    "Chemistry - Atoms and Molecules",
    "Chemistry - Carbon and Compounds",
    "Chemistry - Chemical Reactions",
    "Coding-Decoding",
    "Direction Sense",
    "General Awareness - Miscellaneous",
    "General Science - Miscellaneous",
    "Geometry",
    "Mathematical Operations",
    "Mensuration",
    "Number Series",
    "Number System",
    "Percentage",
    "Physics - Fluids",
    "Physics - Gravitation",
    "Physics - Light",
    "Physics - Motion",
    "Profit and Loss",
    "Puzzle Arrangement",
    "Ratio and Proportion",
    "Seating/Ranking Arrangement",
    "Simple Interest",
    "Speed Time and Distance",
    "Statistics",
    "Time and Work",
    "Trigonometry",
}

ADVANCED_TOPICS = {
    "Compound Interest",
    "Physics - Electricity and Magnetism",
}

ADVANCED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"compound interest",
        r"successively",
        r"combined focal length",
        r"equations? of motion",
        r"convex mirror|concave lens|convex lens",
        r"power of .*lens",
        r"if .* and .* together can complete",
        r"four candidates|registered voters",
        r"ab\(a \+ b\)|3abc",
        r"interchanged .* equation",
        r"seven boxes",
        r"statement 1:|statement 2:",
        r"not true|incorrect",
    ]
]

BASIC_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"which article",
        r"who was|who is|which country|which instrument|which element",
        r"what is the primary",
        r"what distinguishes",
        r"represents which",
        r"example of",
        r"mainly as",
        r"mainly from",
        r"first president",
        r"chosen as",
    ]
]


def text_of(question: dict) -> str:
    return " ".join(
        str(part or "")
        for part in [
            question.get("question"),
            " ".join(question.get("options") or []),
            question.get("topic"),
        ]
    )


def difficulty_for(question: dict) -> tuple[str, str, str]:
    text = text_of(question)
    topic = question.get("topic")
    subject = question.get("subject")
    question_len = len(str(question.get("question") or "").split())

    for pattern in ADVANCED_PATTERNS:
        if pattern.search(text):
            return "advanced", "advanced_pattern", pattern.pattern

    if subject == "General Intelligence and Reasoning" and topic in {"Puzzle Arrangement", "Seating/Ranking Arrangement"}:
        return "advanced", "reasoning_arrangement_topic", topic

    for pattern in BASIC_PATTERNS:
        if pattern.search(text):
            return "basic", "basic_pattern", pattern.pattern

    if topic in ADVANCED_TOPICS:
        return "advanced", "topic_default", topic
    if topic in BASIC_TOPICS:
        return "basic", "topic_default", topic

    if subject == "Mathematics":
        if question_len >= 38:
            return "advanced", "math_word_length", f"words={question_len}"
        return "intermediate", "subject_topic_default", topic or subject

    if subject == "General Intelligence and Reasoning":
        return "intermediate", "subject_topic_default", topic or subject

    if subject == "General Science":
        if question_len >= 34:
            return "intermediate", "science_word_length", f"words={question_len}"
        return "basic", "science_default", topic or subject

    if subject == "General Awareness":
        return "basic", "general_awareness_default", topic or subject

    if topic in INTERMEDIATE_TOPICS:
        return "intermediate", "topic_default", topic

    return "intermediate", "fallback_default", subject or "unknown"


def subject_slug(subject: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    output = deepcopy(payload)
    output["source_layer"] = SOURCE_FILE.name
    output["difficulty_tagging"] = {
        "method": "rule_based_topic_and_text_heuristics",
        "levels": ["basic", "intermediate", "advanced"],
    }

    difficulty_counts = Counter()
    subject_difficulty_counts = Counter()
    topic_difficulty_counts = Counter()
    method_counts = Counter()

    for question in output.get("questions", []):
        difficulty, method, evidence = difficulty_for(question)
        question["difficulty"] = difficulty
        question["difficulty_tagging"] = {
            "method": method,
            "evidence": evidence,
        }
        difficulty_counts[difficulty] += 1
        method_counts[method] += 1
        subject_difficulty_counts[f"{question.get('subject')}|{difficulty}"] += 1
        topic_difficulty_counts[f"{question.get('topic')}|{difficulty}"] += 1

    COMBINED_OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    by_subject = {}
    for question in output.get("questions", []):
        by_subject.setdefault(question["subject"], []).append(question)

    output_files = [COMBINED_OUT.name]
    for subject, questions in sorted(by_subject.items()):
        out_file = OUT_DIR / f"technician-grade-3-2026-{subject_slug(subject)}.difficulty-tagged.json"
        subject_payload = {
            "exam": output["exam"],
            "language": output["language"],
            "subject": subject,
            "question_count": len(questions),
            "questions": questions,
            "source_layer": SOURCE_FILE.name,
            "difficulty_tagging": output["difficulty_tagging"],
        }
        out_file.write_text(json.dumps(subject_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        output_files.append(out_file.name)

    by_subject_difficulty = {}
    for key, count in sorted(subject_difficulty_counts.items()):
        subject, difficulty = key.split("|", 1)
        by_subject_difficulty.setdefault(subject, {})[difficulty] = count

    by_topic_difficulty = {}
    for key, count in sorted(topic_difficulty_counts.items()):
        topic, difficulty = key.split("|", 1)
        by_topic_difficulty.setdefault(topic, {})[difficulty] = count

    summary = {
        "exam": output["exam"],
        "language": output["language"],
        "source_scope": output["source_scope"],
        "source_file": SOURCE_FILE.name,
        "question_count": len(output.get("questions", [])),
        "difficulty_counts": dict(sorted(difficulty_counts.items())),
        "tagging_method_counts": dict(sorted(method_counts.items())),
        "by_subject_difficulty": by_subject_difficulty,
        "by_topic_difficulty": by_topic_difficulty,
        "output_files": [*output_files, SUMMARY_OUT.name],
        "notes": [
            "Difficulty tags are rule-based first-pass labels.",
            "The labels are intended for app filtering and later review, not final psychometric calibration.",
            "Difficulty levels use basic/intermediate/advanced to match the existing prompt style.",
        ],
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
