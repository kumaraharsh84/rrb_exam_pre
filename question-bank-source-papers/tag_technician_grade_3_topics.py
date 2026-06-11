import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path


BASE = Path(__file__).resolve().parent
SOURCE_DIR = BASE / "bank-ready-json" / "technician-grade-3"
OUT_DIR = BASE / "topic-tagged-json" / "technician-grade-3"
SOURCE_FILE = SOURCE_DIR / "technician-grade-3-2026-bank-ready.json"
COMBINED_OUT = OUT_DIR / "technician-grade-3-2026-topic-tagged.json"
SUMMARY_OUT = OUT_DIR / "technician-grade-3-2026-topic-tagging-summary.json"


def rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


TOPIC_RULES = {
    "Mathematics": [
        ("Time and Work", [rx(r"\bwork\b|\btask\b|\bworkers?\b|\bfinish\b|\bdays?\b.*\balone\b|machines? produce|items? in \d+ hours?")]),
        ("Compound Interest", [rx(r"compound interest|becomes thrice|compounded")]),
        ("Simple Interest", [rx(r"simple interest|per annum|principal|borrow|lends?")]),
        ("Percentage", [rx(r"percent|percentage|%\b|successively|depreciat|appreciat|scored .*%|registered voters|monthly income|household expenditure|spends? \d+%|spent \d+%")]),
        ("Average", [rx(r"\baverage\b|\bmean\b")]),
        ("Ratio and Proportion", [rx(r"\bratio\b|proportion|mean proportional|continued proportion|\ba\s*:\s*b\b")]),
        ("Age Problems", [rx(r"\bage\b|present age|years old")]),
        ("Mensuration", [rx(r"cylinder|cone|sphere|circle|radius|diameter|area|volume|perimeter|surface area|cm2|cm3")]),
        ("Geometry", [rx(r"polygon|triangle|angle bisector|exterior angles?|interior angle|angle|regular polygon")]),
        ("Statistics", [rx(r"median|mode|data|frequency")]),
        ("Algebra", [rx(r"simplify|equation|polynomial|coefficient|expansion|value of x|value of y|expression|factor|\bab\b|\bbc\b|\bca\b")]),
        ("Number System", [rx(r"number is|numbers are|divisible|remainder|HCF|LCM|least common|greatest common|digit|co-?prime|positive integers|value of \d+\s*-\s*\d+")]),
        ("Profit and Loss", [rx(r"profit|loss|cost price|selling price|discount|marked price")]),
        ("Speed Time and Distance", [rx(r"speed|distance|train|km/h|metres?|travel|journey")]),
        ("Trigonometry", [rx(r"sin|cos|tan|trigonometric")]),
    ],
    "General Intelligence and Reasoning": [
        ("Coding-Decoding", [rx(r"code language|coded as|code for|decoded")]),
        ("Alphabet Series", [rx(r"alphabetical order|letter-cluster|letters? will remain|english alphabetical|group of letters|subsequent one")]),
        ("Number Series", [rx(r"series|come in place|what should come|missing number")]),
        ("Analogy", [rx(r"same pattern|related in the same way|is related to|following the same logic|analog")]),
        ("Odd One Out", [rx(r"does not belong|odd|alike in a certain way")]),
        ("Seating/Ranking Arrangement", [rx(r"\brow\b|facing north|position from|left end|right end|sits?|rank")]),
        ("Mathematical Operations", [rx(r"interchanged|following equation|operators?|[+x÷-].*=")]),
        ("Puzzle Arrangement", [rx(r"boxes?|kept one over|kept above|kept below|immediately above|immediately below")]),
        ("Direction Sense", [rx(r"north|south|east|west|turns?|direction")]),
        ("Blood Relations", [rx(r"father|mother|brother|sister|son|daughter|wife|husband|relation")]),
        ("Syllogism", [rx(r"statements?|conclusions?|all .* are|some .* are|no .* are")]),
        ("Venn Diagram", [rx(r"venn|diagram")]),
        ("Calendar and Clock", [rx(r"calendar|clock|time|day of the week|mirror image")]),
    ],
    "General Science": [
        ("Physics - Gravitation", [rx(r"gravitation|gravitational|gravity|earth and the moon")]),
        ("Physics - Motion", [rx(r"velocity|acceleration|equations of motion|uniform velocity|force|newton|inertia")]),
        ("Physics - Sound", [rx(r"sound|concert hall|echo|frequency|amplitude|audible")]),
        ("Physics - Electricity and Magnetism", [rx(r"resistivity|current|wire|magnetic|circuit|voltage|power|electric|filament|tungsten|oven|symbol represent")]),
        ("Physics - Light", [rx(r"lens|mirror|image formed|convex|concave|prism|white light|bending of light|deviation|focal|power of lens")]),
        ("Physics - Fluids", [rx(r"immersed in water|buoyancy|float|pressure|density")]),
        ("Chemistry - Mixtures and Solutions", [rx(r"suspension|solution|solute|solvent|concentration|homogeneous mixture|particles of solute|scatter light")]),
        ("Chemistry - Chemical Reactions", [rx(r"double displacement|reacts with water|reaction occur|metal to each test tube|chemical reaction|potassium reacts")]),
        ("Chemistry - Carbon and Compounds", [rx(r"homologous|carbon|hydrocarbon|organic|\bCH\d?\b|–CH|−CH|-CH")]),
        ("Chemistry - Atoms and Molecules", [rx(r"hydrogen|oxygen|water contains|mole|atoms?|molecules?|chemical formula")]),
        ("Chemistry - Acids Bases and Salts", [rx(r"acid|base|salt|pH|neutralisation")]),
        ("Chemistry - Metals and Non-metals", [rx(r"metals? and non-metals?|alloy|zinc|galvan|rust|corrosion|bleaching powder|element|symbol")]),
        ("Biology - Tissues", [rx(r"epithelial|connective tissue|tissue")]),
        ("Biology - Reproduction", [rx(r"binary fission|splits into two|reproduction|budding|fragmentation")]),
        ("Biology - Ecology", [rx(r"biological magnification|pesticide|food chain|ecosystem|environment")]),
        ("Biology - Human Body", [rx(r"human|blood|heart|lungs?|respiratory|digestive|intestine|kidney|brain")]),
        ("Biology - Cell Biology", [rx(r"cell|nucleus|mitochondria|chloroplast|organelles?")]),
        ("Biology - Agriculture", [rx(r"crop|yield|nutrients?|soil|poultry|broilers?|layers?|weed|irrigation|check-dams?|farming")]),
        ("Biology - Plant Physiology", [rx(r"xylem|phloem|floral|fertilisation|plant")]),
        ("General Science - Miscellaneous", [rx(r".+")]),
    ],
    "General Awareness": [
        ("Current Affairs", [rx(r"recent|in june|in \d{4}|deal|appointed|appointment|chairman|budget|union budget")]),
        ("Sports", [rx(r"medal|archery|world cup|sports?|championship|tournament")]),
        ("Science and Technology", [rx(r"satellite|GSAT|communication satellite|technology|deep tech")]),
        ("Indian History", [rx(r"indian national congress|INC|british indian|bal gangadhar tilak|session|movement|slogan")]),
        ("Indian Polity", [rx(r"article|constitution|commission|union territory|supreme court|parliament|president|governor")]),
        ("Indian Geography", [rx(r"river|plateau|drainage|mineral|chota nagpur|luni|resources")]),
        ("Art and Culture", [rx(r"dancer|odissi|book|author|literature|music|dance|heart lamp")]),
        ("Economy and Schemes", [rx(r"farmers?|scheme|agricultural|transportation|bank|finance")]),
        ("General Awareness - Miscellaneous", [rx(r".+")]),
    ],
}


def tag_topic(question: dict) -> tuple[str | None, str, str]:
    subject = question.get("subject")
    text = " ".join(
        str(part or "")
        for part in [
            question.get("question"),
            " ".join(question.get("options") or []),
        ]
    )
    rules = TOPIC_RULES.get(subject, [])
    for topic, patterns in rules:
        for pattern in patterns:
            if pattern.search(text):
                confidence = "fallback" if topic.endswith("Miscellaneous") else "rule"
                return topic, confidence, pattern.pattern
    return None, "untagged", ""


def subject_slug(subject: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    tagged_payload = deepcopy(payload)
    tagged_payload["source_layer"] = SOURCE_FILE.name
    tagged_payload["topic_tagging"] = {
        "method": "rule_based_keyword_tagging",
        "topic_only": True,
        "difficulty_tagging": False,
    }

    topic_counts = Counter()
    subject_topic_counts = Counter()
    method_counts = Counter()
    tagged_questions = []

    for question in tagged_payload.get("questions", []):
        topic, method, matched_rule = tag_topic(question)
        question["topic"] = topic
        question["topic_tagging"] = {
            "method": method,
            "matched_rule": matched_rule,
        }
        tagged_questions.append(question)
        topic_counts[topic or "UNTAGGED"] += 1
        subject_topic_counts[f"{question.get('subject')}|{topic or 'UNTAGGED'}"] += 1
        method_counts[method] += 1

    COMBINED_OUT.write_text(json.dumps(tagged_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    by_subject = {}
    for question in tagged_questions:
        by_subject.setdefault(question["subject"], []).append(question)

    output_files = [COMBINED_OUT.name]
    for subject, questions in sorted(by_subject.items()):
        out_file = OUT_DIR / f"technician-grade-3-2026-{subject_slug(subject)}.topic-tagged.json"
        subject_payload = {
            "exam": tagged_payload["exam"],
            "language": tagged_payload["language"],
            "subject": subject,
            "question_count": len(questions),
            "questions": questions,
            "source_layer": SOURCE_FILE.name,
            "topic_tagging": tagged_payload["topic_tagging"],
        }
        out_file.write_text(json.dumps(subject_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        output_files.append(out_file.name)

    nested_subject_counts = {}
    for key, count in sorted(subject_topic_counts.items()):
        subject, topic = key.split("|", 1)
        nested_subject_counts.setdefault(subject, {})[topic] = count

    summary = {
        "exam": tagged_payload["exam"],
        "language": tagged_payload["language"],
        "source_scope": tagged_payload["source_scope"],
        "source_file": SOURCE_FILE.name,
        "question_count": len(tagged_questions),
        "tagged_questions": sum(1 for question in tagged_questions if question.get("topic")),
        "untagged_questions": sum(1 for question in tagged_questions if not question.get("topic")),
        "tagging_method_counts": dict(sorted(method_counts.items())),
        "by_topic": dict(sorted(topic_counts.items())),
        "by_subject_topic": nested_subject_counts,
        "output_files": [*output_files, SUMMARY_OUT.name],
        "notes": [
            "Topic tags are rule-based and transparent.",
            "Difficulty is intentionally unchanged for a later pass.",
            "Fallback miscellaneous tags should be reviewed before final app merge.",
        ],
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
