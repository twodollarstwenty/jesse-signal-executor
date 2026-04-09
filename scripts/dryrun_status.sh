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
  ps eww -p "${pid}" -o command= 2>/dev/null || true
}

find_running_pid_for_script() {
  local heartbeat_file="$1"
  local heartbeat_env_name="$2"
  local pid command

  while read -r pid command; do
    if [[ -n "${pid}" ]] && [[ "${command}" == *"${heartbeat_env_name}=${heartbeat_file}"* ]]; then
      printf '%s\n' "${pid}"
      return 0
    fi
  done < <(ps eww -ax -o pid= -o command=)
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
  local heartbeat_env_name="$5"

  local pid=""
  local discovered_without_pid=0
  if [[ -f "${pid_file}" ]]; then
    pid="$(<"${pid_file}")"
  else
    pid="$(find_running_pid_for_script "${heartbeat_file}" "${heartbeat_env_name}" | head -n 1)"
    if [[ -n "${pid}" ]]; then
      discovered_without_pid=1
    fi
  fi

  if [[ -z "${pid}" ]]; then
    printf '%s: stopped\n' "${name}"
    return
  fi

  if ! kill -0 "${pid}" 2>/dev/null; then
    [[ -f "${pid_file}" ]] && rm -f "${pid_file}"
    printf '%s: stale\n' "${name}"
    return
  fi

  if (( discovered_without_pid == 0 )) && ! pid_matches_script "${pid}" "${expected_script}"; then
    [[ -f "${pid_file}" ]] && rm -f "${pid_file}"
    printf '%s: stopped\n' "${name}"
    return
  fi

  if [[ ! -f "${heartbeat_file}" ]]; then
    local started_at now
    if [[ -f "${pid_file}" ]]; then
      started_at="$(stat -f %m "${pid_file}")"
      now="$(date +%s)"
      if (( now - started_at <= STARTUP_GRACE_SECONDS )); then
        printf '%s: running (pid=%s)\n' "${name}" "${pid}"
        return
      fi
    fi
  fi

  if "${PYTHON_BIN}" "${CHECK_HEARTBEAT}" --path "${heartbeat_file}" --max-age-seconds 60 >/dev/null 2>&1; then
    printf '%s: running (pid=%s)\n' "${name}" "${pid}"
    return
  fi

  printf '%s: stale (pid=%s)\n' "${name}" "${pid}"
}

show_dryrun_status() {
  show_process_status "executor" "${PID_DIR}/executor.pid" "${HEARTBEAT_DIR}/executor.heartbeat" "${REPO_ROOT}/scripts/run_executor_loop.py" "EXECUTOR_HEARTBEAT_PATH"
  show_process_status "jesse-dryrun" "${PID_DIR}/jesse-dryrun.pid" "${HEARTBEAT_DIR}/jesse-dryrun.heartbeat" "${REPO_ROOT}/scripts/run_jesse_dryrun_loop.py" "JESSE_HEARTBEAT_PATH"
}

show_dryrun_status
