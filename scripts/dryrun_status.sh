#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

export REPO_ROOT

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

"${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_dryrun_supervisor.py" status "$@"
