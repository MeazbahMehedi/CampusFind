"""Cross-platform first-run helper. Run with --demo for fictional sample data."""

import argparse
from pathlib import Path
import subprocess
import sys
import venv

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--demo", action="store_true", help="Seed an empty database with fictional examples."
)
args = parser.parse_args()
if sys.version_info < (3, 11):
    raise SystemExit("Please install Python 3.11 or newer.")
venv_dir = root / ".venv"
python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
if not python.exists():
    print("Creating your virtual environment…", flush=True)
    venv.EnvBuilder(with_pip=True).create(venv_dir)
subprocess.run(
    [str(python), "-m", "pip", "install", "-r", "requirements-lock.txt"], cwd=root, check=True
)
subprocess.run(
    [str(python), "-m", "flask", "--app", "campusfind:create_app", "init-db"], cwd=root, check=True
)
configured_admin = (root / "instance" / "admin-bootstrap.json").exists()
if configured_admin:
    subprocess.run(
        [str(python), "-m", "flask", "--app", "campusfind:create_app", "configure-admin"],
        cwd=root,
        check=True,
    )
if args.demo:
    subprocess.run(
        [str(python), "-m", "flask", "--app", "campusfind:create_app", "seed-demo"],
        cwd=root,
        check=True,
    )
elif not configured_admin:
    print("Next, create an administrator:")
    print(f'"{python}" -m flask --app campusfind:create_app create-admin')
print("Ready. Start with start.bat (Windows) or ./start.sh (Linux/macOS).")
