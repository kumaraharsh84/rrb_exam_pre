import json
import re
from pathlib import Path

log_path = Path(r'C:\Users\kumar\.gemini\antigravity-ide\brain\ef339e1a-a0c7-431e-96a6-ed4b9d43de66\.system_generated\logs\transcript.jsonl')
out_dir = Path(r'c:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers')

files_to_recover = [
    'parse_ntpc.py', 'normalize_ntpc.py', 'recover_ntpc_ocr.py',
    'hybrid_repair_ntpc.py', 'build_ntpc_repaired_layer.py',
    'recover_answers_ntpc.py', 'build_ntpc_quality_gated_layer.py'
]

contents = {f: None for f in files_to_recover}

for line in log_path.read_text('utf-8').splitlines():
    if not line.strip():
        continue
    try:
        obj = json.loads(line)
    except:
        continue
        
    if obj.get('type') == 'PLANNER_RESPONSE':
        tool_calls = obj.get('tool_calls', [])
        for call in tool_calls:
            if call.get('name') == 'write_to_file':
                args = call.get('args', {})
                target = args.get('TargetFile', '')
                for f in files_to_recover:
                    if target.endswith(f):
                        contents[f] = args.get('CodeContent', '')
                        
for f, content in contents.items():
    if content:
        out_path = out_dir / f
        out_path.write_text(content, encoding='utf-8')
        print(f'Recovered {f} from write_to_file calls')
