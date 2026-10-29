"""Apply migrations then start Waitress. Does not create accounts or demo data."""

from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
subprocess.run(
    [sys.executable, "-m", "flask", "--app", "campusfind:create_app", "init-db"],
    cwd=root,
    check=True,
)
subprocess.run([sys.executable, "run.py"], cwd=root, check=True)
