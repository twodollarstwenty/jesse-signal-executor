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

wait_for_exit() {
  local pid="$1"

  for _ in 1 2 3 4 5; do
    if ! kill -0 "${pid}" 2>/dev/null; then
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
  local heartbeat_file="$4"
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
    printf '%s already stopped\n' "${name}"
    return
  fi

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null || { (( discovered_without_pid == 0 )) && ! pid_matches_script "${pid}" "${expected_script}"; }; then
    rm -f "${pid_file}"
    printf 'cleaned stale pid for %s\n' "${name}"
    return
  fi

  kill "${pid}"

  if ! wait_for_exit "${pid}"; then
    printf 'failed to stop %s (pid=%s)\n' "${name}" "${pid}" >&2
    return 1
  fi

  rm -f "${pid_file}"

  local extra_pid
  while true; do
    extra_pid="$(find_running_pid_for_script "${heartbeat_file}" "${heartbeat_env_name}" | head -n 1)"
    if [[ -z "${extra_pid}" ]]; then
      break
    fi

    if ! kill "${extra_pid}" 2>/dev/null; then
      printf 'failed to stop %s child process (pid=%s)\n' "${name}" "${extra_pid}" >&2
      return 1
    fi

    if ! wait_for_exit "${extra_pid}"; then
      printf 'failed to stop %s child process (pid=%s)\n' "${name}" "${extra_pid}" >&2
      return 1
    fi
  done

  printf 'stopped %s (pid=%s)\n' "${name}" "${pid}"
}

stop_dryrun_processes() {
  stop_process "executor" "${PID_DIR}/executor.pid" "${REPO_ROOT}/scripts/run_executor_loop.py" "${RUNTIME_DIR}/heartbeats/executor.heartbeat" "EXECUTOR_HEARTBEAT_PATH"
  stop_process "jesse-dryrun" "${PID_DIR}/jesse-dryrun.pid" "${REPO_ROOT}/scripts/run_jesse_dryrun_loop.py" "${RUNTIME_DIR}/heartbeats/jesse-dryrun.heartbeat" "JESSE_HEARTBEAT_PATH"
}

stop_dryrun_processes
