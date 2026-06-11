import json
import re
import subprocess
from pathlib import Path

BASE = Path(r"c:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers")
PDF_DIR = BASE / "ntpc"
TXT_DIR = BASE / "extracted-text" / "ntpc"
PARSED_DIR = BASE / "parsed-json" / "ntpc"
OUT_DIR = BASE / "ocr-recovered-json" / "ntpc"
IMG_TMP_DIR = BASE / "ocr-tmp-images"

PDFTOPPM = Path(
    r"C:\Users\kumar\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin\pdftoppm.exe"
)
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

QUESTION_RE = re.compile(r"(?m)^\s*Q\.(\d+)")
OCR_Q_SPLIT_RE = re.compile(r"(?i)(?:^|\n)\s*Q\s*\.\s*(\d+)")

def pdf_page_count(pdf_path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True)
    match = re.search(r"^Pages:\s*(\d+)", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not read page count for {pdf_path}")
    return int(match.group(1))

def page_questions(page: int, txt_path: Path) -> list[int]:
    # Need to split txt by \f
    text = txt_path.read_text(encoding="utf-8", errors="replace")
    pages = text.split('\x0c')
    if page - 1 < len(pages):
        page_text = pages[page - 1]
        return [int(value) for value in QUESTION_RE.findall(page_text)]
    return []

def run_ocr_on_page(pdf_path: Path, page: int) -> str:
    IMG_TMP_DIR.mkdir(parents=True, exist_ok=True)
    img_prefix = IMG_TMP_DIR / f"page_{page}"
    
    # Render exactly one page
    subprocess.run([
        str(PDFTOPPM),
        "-f", str(page),
        "-l", str(page),
        "-r", "300", # Higher resolution for OCR
        "-png",
        str(pdf_path),
        str(img_prefix)
    ], check=True)
    
    # pdftoppm appends -1, -01 etc.
    # Find the generated file
    generated_imgs = list(IMG_TMP_DIR.glob(f"page_{page}-*.png"))
    if not generated_imgs:
        return ""
    actual_img = generated_imgs[0]
    
    # Run Tesseract
    out_txt = IMG_TMP_DIR / f"ocr_{page}"
    subprocess.run([TESSERACT_CMD, str(actual_img), str(out_txt)], check=True)
    
    res = out_txt.with_suffix('.txt').read_text(encoding='utf-8', errors='replace')
    
    # Clean up temp files
    actual_img.unlink(missing_ok=True)
    out_txt.with_suffix('.txt').unlink(missing_ok=True)
    
    return res

def process_pdf(parsed_path: Path):
    data = json.loads(parsed_path.read_text(encoding="utf-8"))
    pdf_name = data["paper"].replace(".txt", ".pdf")
    pdf_path = PDF_DIR / pdf_name
    txt_path = TXT_DIR / data["paper"]
    
    if not pdf_path.exists():
        return data
        
    page_count = pdf_page_count(pdf_path)
    
    # Create a quick lookup for questions that are missing text
    # A question is considered missing if length < 10 or it contains no alphabetic characters
    missing_qs = {}
    for q in data["questions"]:
        q_text = q.get("question", "").strip()
        if len(q_text) < 10 or not any(c.isalpha() for c in q_text):
            missing_qs[q["question_number"]] = q
            
    if not missing_qs:
        return data
        
    print(f"[{pdf_name}] Found {len(missing_qs)} missing questions. Running OCR...")
    
    # Iterate through pages, find which pages contain the missing questions
    for page in range(1, page_count + 1):
        qs_on_page = page_questions(page, txt_path)
        missing_on_page = [q_num for q_num in qs_on_page if q_num in missing_qs]
        
        if not missing_on_page:
            continue
            
        print(f"  OCR page {page} for questions {missing_on_page}...")
        ocr_text = run_ocr_on_page(pdf_path, page)
        
        # Split OCR text by Q.X
        parts = OCR_Q_SPLIT_RE.split(ocr_text)
        
        # parts[0] is everything before the first Q.X
        # parts[1] is the first Q.X number
        # parts[2] is the text for Q.X, and so on
        for i in range(1, len(parts), 2):
            try:
                q_num = int(parts[i])
                q_body = parts[i+1].strip()
                if q_num in missing_qs:
                    missing_qs[q_num]["question"] = q_body
                    missing_qs[q_num]["ocr_recovered"] = True
            except ValueError:
                pass
                
    return data

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parsed_files = sorted(PARSED_DIR.glob("*.parsed.json"))
    
    total_recovered = 0
    for parsed_path in parsed_files:
        out_path = OUT_DIR / parsed_path.name
        
        if out_path.exists():
            print(f"Skipping {parsed_path.name}, already OCR'd.")
            continue
            
        data = process_pdf(parsed_path)
        
        # Count recovered
        recovered = sum(1 for q in data["questions"] if q.get("ocr_recovered"))
        total_recovered += recovered
        
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        
    print(f"Total questions OCR recovered: {total_recovered}")

if __name__ == "__main__":
    main()
