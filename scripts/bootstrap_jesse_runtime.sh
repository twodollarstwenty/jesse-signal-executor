#!/usr/bin/env bash
set -euo pipefail

python3 -m venv runtime/jesse_workspace/.venv
source runtime/jesse_workspace/.venv/bin/activate
python3 -m pip install -r runtime/jesse_workspace/requirements.txt
echo "jesse runtime bootstrap complete"
