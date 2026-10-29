#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Run python3 setup_project.py --demo first.'
  exit 1
fi
exec .venv/bin/python run.py
