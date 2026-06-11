import json
import re
from pathlib import Path

BASE = Path(r"c:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
OCR_DIR = BASE / "ocr-recovered-json" / "ntpc"

# Regex to find Q1, Q 2, Q.3, Q . 4
# We use a positive lookahead to keep the matched string or just split and keep the numbers
BETTER_SPLIT_RE = re.compile(r"(?i)(?:^|\s+)Q\s*\.?\s*(\d+)\s*")

def fix_file(file_path: Path):
    data = json.loads(file_path.read_text(encoding="utf-8"))
    
    # We will build a mapping of all question numbers to their question dicts
    q_dict = {q["question_number"]: q for q in data["questions"]}
    
    for q in data["questions"]:
        if q.get("ocr_recovered"):
            text = q["question"]
            
            # See if this text contains other questions
            parts = BETTER_SPLIT_RE.split(text)
            
            # parts[0] is the text BEFORE any QX
            # parts[1] is the first QX number
            # parts[2] is the text for QX
            
            if len(parts) > 1:
                # This text swallowed other questions!
                # We need to distribute it.
                
                # First, the text before the first QX is actually the text for the CURRENT question (e.g. Q1)
                # Wait, does the text START with Q1?
                # If the original text started with "Q1...", then parts[0] is empty, parts[1] is "1".
                # But wait, the original `recover_ntpc_ocr.py` split the text and assigned `q_body` to Q1.
                # So the text in Q1 DOES NOT start with "Q.1"! It starts with the actual question body!
                # "The area of a rhombus is 96 cm? ... Q2 Which type of soil..."
                # So parts[0] is Q1's true text!
                
                q["question"] = parts[0].strip()
                
                # Now distribute the rest
                for i in range(1, len(parts), 2):
                    try:
                        q_num = int(parts[i])
                        q_body = parts[i+1].strip()
                        if q_num in q_dict:
                            q_dict[q_num]["question"] = q_body
                            q_dict[q_num]["ocr_recovered"] = True
                    except ValueError:
                        pass

    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
def main():
    for f in OCR_DIR.glob("*.parsed.json"):
        fix_file(f)
    print("Fixed OCR splitting issues.")

if __name__ == "__main__":
    main()
