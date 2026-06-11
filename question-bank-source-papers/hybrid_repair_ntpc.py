import json
import re
from pathlib import Path

BASE = Path(r"C:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
SRC_DIR = BASE / "normalized-json" / "ntpc"
OUT_DIR = BASE / "repaired-json" / "ntpc"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH = BASE / "repaired-json" / "ntpc-repair-summary.json"

# Regex to find options in the text. e.g. "1. some text 2. some text 3. some text 4. some text"
# or "(A) some text (B) some text (C) some text (D) some text"
# but NTPC options are typically 1. 2. 3. 4.
OPTION_SPLIT_RE = re.compile(r"(?:\n|^)\s*(?:[1-4]\.|[A-D]\.)\s*(.*?)(?=(?:\n\s*(?:[1-4]\.|[A-D]\.)\s*)|$)", re.IGNORECASE | re.DOTALL)

def repair_question(q: dict) -> dict:
    if not q.get("ocr_recovered"):
        return q
        
    text = q["question"]
    # If the text has option numbers, let's extract them
    # Find all matches of 1., 2., 3., 4.
    
    # We will use a simpler approach: 
    # Find the position of "1. " or "A. "
    # Sometimes OCR puts "Ans XX 1." or just inline "1."
    match1 = re.search(r"(?:Ans.*?)?\s+(1\.|A\.)\s+", text, re.IGNORECASE)
    if not match1:
        # Try without \s+ at the start if it's exactly the first thing
        match1 = re.search(r"(?:Ans.*?)?(?:1\.|A\.)\s+", text, re.IGNORECASE)
        if not match1:
            return q
        
    question_part = text[:match1.start()].strip()
    options_part = text[match1.start():].strip()
    
    # Extract 4 options
    opts = []
    # Split by \s1. or \n2. etc
    # We use a lookahead to split but we want to split by the number prefix
    parts = re.split(r"(?:Ans.*?)?\s*(?:[1-4A-D]\.)\s+", " " + options_part, flags=re.IGNORECASE)
    # parts[0] is empty
    for part in parts[1:]:
        cleaned = part.strip()
        if cleaned:
            opts.append(cleaned)
            
    # Remove the junk "Option 1 ID" from the last option if present
    if opts:
        last_opt = opts[-1]
        junk_idx = last_opt.find("Option 1 ID")
        if junk_idx != -1:
            opts[-1] = last_opt[:junk_idx].strip()
            
    if len(opts) >= 4:
        q["question"] = question_part
        # Replace the first 4 options
        for i in range(4):
            # preserve the prefix 1. 2. 3. 4.
            prefix = f"{i+1}. "
            q["options"][i] = prefix + opts[i]
            
    return q

def process_file(src_path: Path):
    data = json.loads(src_path.read_text("utf-8"))
    repaired_count = 0
    for q in data["questions"]:
        orig = q["question"]
        q = repair_question(q)
        if q["question"] != orig:
            repaired_count += 1
            
    return data, repaired_count

def main():
    total_repaired = 0
    for src in SRC_DIR.glob("*.normalized.json"):
        data, count = process_file(src)
        total_repaired += count
        out_name = src.name.replace(".normalized.json", ".repaired.json")
        (OUT_DIR / out_name).write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        
    print(f"Total questions repaired/structured: {total_repaired}")
    
if __name__ == "__main__":
    main()
