#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${DRYRUN_RUNTIME_DIR:-${REPO_ROOT}/runtime/dryrun}"
PID_DIR="${RUNTIME_DIR}/pids"

get_command_line() {
  local pid="$1"
  ps eww -p "${pid}" -o command= 2>/dev/null || true
}

pid_matches_script() {
  local pid="$1"
  local expected_script="$2"
  local command_line
  command_line="$(get_command_line "${pid}")"

  [[ -n "${command_line}" ]] && [[ "${command_line}" == *"${expected_script}"* ]]
}

wait_for_exit() {
  local pid="$1"
  local expected_script="$2"

  for _ in 1 2 3 4 5; do
    if ! kill -0 "${pid}" 2>/dev/null || ! pid_matches_script "${pid}" "${expected_script}"; then
      return 0
    fi

    sleep 0.2
  done

  return 1
}

stop_process() {
  local name="$1"
  local pid_file="$2"
  local expected_script="$3"

  if [[ ! -f "${pid_file}" ]]; then
    printf '%s already stopped\n' "${name}"
    return
  fi

  local pid
  pid="$(<"${pid_file}")"

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null || ! pid_matches_script "${pid}" "${expected_script}"; then
    rm -f "${pid_file}"
    printf 'cleaned stale pid for %s\n' "${name}"
    return
  fi

  kill "${pid}"

  if ! wait_for_exit "${pid}" "${expected_script}"; then
    printf 'failed to stop %s (pid=%s)\n' "${name}" "${pid}" >&2
    return 1
  fi

  rm -f "${pid_file}"
  printf 'stopped %s (pid=%s)\n' "${name}" "${pid}"
}

stop_dryrun_processes() {
  stop_process "executor" "${PID_DIR}/executor.pid" "${REPO_ROOT}/scripts/run_executor_loop.py"
  stop_process "jesse-dryrun" "${PID_DIR}/jesse-dryrun.pid" "${REPO_ROOT}/scripts/run_jesse_dryrun_loop.py"
}

stop_dryrun_processes
