#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

export REPO_ROOT

python3 "${REPO_ROOT}/scripts/run_dryrun_supervisor.py" stop "$@"
