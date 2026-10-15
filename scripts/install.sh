#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
"${PYTHON:-python3}" -c 'import sys; assert (3, 10) <= sys.version_info[:2] <= (3, 12), "Use Python 3.10–3.12 (MediaPipe compatibility)"'
if [ ! -d venv ]; then "${PYTHON:-python3}" -m venv venv; fi
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m pip check
