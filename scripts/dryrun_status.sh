#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${DRYRUN_RUNTIME_DIR:-${REPO_ROOT}/runtime/dryrun}"
PID_DIR="${RUNTIME_DIR}/pids"
HEARTBEAT_DIR="${RUNTIME_DIR}/heartbeats"
CHECK_HEARTBEAT="${REPO_ROOT}/scripts/check_heartbeat.py"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
STARTUP_GRACE_SECONDS="${DRYRUN_STARTUP_GRACE_SECONDS:-5}"

get_command_line() {
  local pid="$1"
  ps -p "${pid}" -o command= 2>/dev/null || true
}

pid_matches_script() {
  local pid="$1"
  local expected_script="$2"
  local command_line
  command_line="$(get_command_line "${pid}")"

  [[ -n "${command_line}" ]] && [[ "${command_line}" == *"${expected_script}"* ]]
}

show_process_status() {
  local name="$1"
  local pid_file="$2"
  local heartbeat_file="$3"
  local expected_script="$4"

  if [[ ! -f "${pid_file}" ]]; then
    printf '%s: stopped\n' "${name}"
    return
  fi

  local pid
  pid="$(<"${pid_file}")"

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    rm -f "${pid_file}"
    printf '%s: stale\n' "${name}"
    return
  fi

  if ! pid_matches_script "${pid}" "${expected_script}"; then
    rm -f "${pid_file}"
    printf '%s: stopped\n' "${name}"
    return
  fi

  if [[ ! -f "${heartbeat_file}" ]]; then
    local pid_started_at
    pid_started_at="$(stat -f %m "${pid_file}")"
    local now
    now="$(date +%s)"

    if (( now - pid_started_at <= STARTUP_GRACE_SECONDS )); then
      printf '%s: running (pid=%s)\n' "${name}" "${pid}"
      return
    fi
  fi

  if "${PYTHON_BIN}" "${CHECK_HEARTBEAT}" --path "${heartbeat_file}" --max-age-seconds 60 >/dev/null 2>&1; then
    printf '%s: running (pid=%s)\n' "${name}" "${pid}"
    return
  fi

  printf '%s: stale (pid=%s)\n' "${name}" "${pid}"
}

show_dryrun_status() {
  show_process_status "executor" "${PID_DIR}/executor.pid" "${HEARTBEAT_DIR}/executor.heartbeat" "${REPO_ROOT}/scripts/run_executor_loop.py"
  show_process_status "jesse-dryrun" "${PID_DIR}/jesse-dryrun.pid" "${HEARTBEAT_DIR}/jesse-dryrun.heartbeat" "${REPO_ROOT}/scripts/run_jesse_dryrun_loop.py"
}

show_dryrun_status
