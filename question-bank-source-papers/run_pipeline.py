import subprocess
import sys

scripts = [
    "normalize_group_d.py",
    "build_group_d_quality_gated_layer.py",
    "recover_answers_group_d.py",
    "build_group_d_bank_ready.py",
    "tag_group_d_topics.py",
    "tag_group_d_difficulty.py",
    "audit_group_d_duplicates.py",
    "build_group_d_app_merge.py"
]

for script in scripts:
    print(f"Running {script}...")
    result = subprocess.run([sys.executable, script])
    if result.returncode != 0:
        print(f"Error: {script} failed with exit code {result.returncode}")
        sys.exit(1)
    print(f"{script} completed successfully.\n")

print("All pipeline scripts completed successfully!")
