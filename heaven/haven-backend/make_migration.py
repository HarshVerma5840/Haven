import os
import shutil
import subprocess

# replace migrations/env.py
shutil.copy("custom_env.py", "migrations/env.py")

# generate migration
subprocess.run([r".\venv\Scripts\alembic", "revision", "--autogenerate", "-m", "Initial migration for weekly_employee_metrics"], check=True)
