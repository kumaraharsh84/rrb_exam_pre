import json
from pathlib import Path
import re

out_dir = Path(r'c:\Users\kumar\OneDrive\Desktop\project\rrb exam pre\rrb-exam-prep\question-bank-source-papers')

# 1. parse_ntpc.py
parse_src = (out_dir / 'parse_technician_grade_3.py').read_text('utf-8')
parse_ntpc = parse_src.replace('technician-grade-3', 'ntpc').replace('technician_grade_3', 'ntpc').replace('Technician Grade 3', 'NTPC')
parse_ntpc = re.sub(r'if "english" not in pdf_path\.name\.lower\(\):\s+continue', '', parse_ntpc)
(out_dir / 'parse_ntpc.py').write_text(parse_ntpc, encoding='utf-8')

# 2. normalize_ntpc.py
norm_src = (out_dir / 'normalize_group_d.py').read_text('utf-8')
norm_ntpc = norm_src.replace('group-d', 'ntpc').replace('group_d', 'ntpc').replace('Group D', 'NTPC')
(out_dir / 'normalize_ntpc.py').write_text(norm_ntpc, encoding='utf-8')

# 3. build_ntpc_quality_gated_layer.py
qg_src = (out_dir / 'build_group_d_quality_gated_layer.py').read_text('utf-8')
qg_ntpc = qg_src.replace('group-d', 'ntpc').replace('group_d', 'ntpc').replace('Group D', 'NTPC')
(out_dir / 'build_ntpc_quality_gated_layer.py').write_text(qg_ntpc, encoding='utf-8')

# 4. recover_answers_ntpc.py
ans_src = (out_dir / 'recover_answers_group_d.py').read_text('utf-8')
ans_ntpc = ans_src.replace('group-d', 'ntpc').replace('group d', 'ntpc').replace('Group D', 'NTPC')
# Empty the MANUAL_VISUAL_ANSWER_FIXES dictionary
ans_ntpc = re.sub(r'MANUAL_VISUAL_ANSWER_FIXES = \{[^}]+\}', 'MANUAL_VISUAL_ANSWER_FIXES = {}', ans_ntpc)
(out_dir / 'recover_answers_ntpc.py').write_text(ans_ntpc, encoding='utf-8')

# 5. Fix build_ntpc_bank_ready.py back to answer-recovered-json
br_path = out_dir / 'build_ntpc_bank_ready.py'
br_src = br_path.read_text('utf-8')
br_src = br_src.replace('"quality-gated-json"', '"answer-recovered-json"')
br_src = br_src.replace('quality-gated-summary.json', 'answer-recovery-summary.json')
br_src = br_src.replace('.quality-gated.json', '.answer-recovered.json')
br_path.write_text(br_src, encoding='utf-8')

print("Successfully generated Phase 1 scripts for NTPC and fixed build_ntpc_bank_ready.py")
