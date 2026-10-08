import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True)
    if result.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(result.returncode)

run(r".\venv\Scripts\python -m compileall app tests")
run(r".\venv\Scripts\pytest")
run(r".\venv\Scripts\alembic check")

print("All validations passed.")
