#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${DRYRUN_RUNTIME_DIR:-${REPO_ROOT}/runtime/dryrun}"
PID_DIR="${RUNTIME_DIR}/pids"
LOG_DIR="${RUNTIME_DIR}/logs"
HEARTBEAT_DIR="${RUNTIME_DIR}/heartbeats"
PYTHONPATH_VALUE="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
POSTGRES_HOST_VALUE="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT_VALUE="${POSTGRES_PORT:-5432}"
POSTGRES_DB_VALUE="${POSTGRES_DB:-jesse_db}"
POSTGRES_USER_VALUE="${POSTGRES_USER:-jesse_user}"
POSTGRES_PASSWORD_VALUE="${POSTGRES_PASSWORD:-password}"

EXECUTOR_PID_FILE="${PID_DIR}/executor.pid"
JESSE_PID_FILE="${PID_DIR}/jesse-dryrun.pid"

EXECUTOR_LOG_FILE="${LOG_DIR}/executor.log"
JESSE_LOG_FILE="${LOG_DIR}/jesse-dryrun.log"

EXECUTOR_HEARTBEAT_FILE="${HEARTBEAT_DIR}/executor.heartbeat"
JESSE_HEARTBEAT_FILE="${HEARTBEAT_DIR}/jesse-dryrun.heartbeat"

EXECUTOR_SCRIPT_PATH="${REPO_ROOT}/scripts/run_executor_loop.py"
JESSE_SCRIPT_PATH="${REPO_ROOT}/scripts/run_jesse_dryrun_loop.py"
EXECUTOR_PYTHON="${DRYRUN_EXECUTOR_PYTHON:-${REPO_ROOT}/.venv/bin/python}"
JESSE_PYTHON="${DRYRUN_JESSE_PYTHON:-${REPO_ROOT}/runtime/jesse_workspace/.venv/bin/python}"
JESSE_BIN_DIR="$(dirname -- "${JESSE_PYTHON}")"

mkdir -p "${PID_DIR}" "${LOG_DIR}" "${HEARTBEAT_DIR}"

get_command_line() {
  local pid="$1"
  ps eww -p "${pid}" -o command= 2>/dev/null || true
}

find_running_pid_for_script() {
  local expected_script="$1"
  local heartbeat_file="$2"
  local pid command

  while read -r pid command; do
    if [[ -n "${pid}" ]] && [[ "${command}" == *"${heartbeat_file}"* ]]; then
      printf '%s\n' "${pid}"
      return 0
    fi
  done < <(ps -ax -o pid= -o command=)
}

pid_matches_script() {
  local pid="$1"
  local expected_script="$2"
  local command_line
  command_line="$(get_command_line "${pid}")"

  [[ -n "${command_line}" ]] && [[ "${command_line}" == *"${expected_script}"* ]]
}

cleanup_stale_pid() {
  local pid_file="$1"
  local expected_script="$2"

  if [[ ! -f "${pid_file}" ]]; then
    return
  fi

  local pid
  pid="$(<"${pid_file}")"

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null || ! pid_matches_script "${pid}" "${expected_script}"; then
    rm -f "${pid_file}"
  fi
}

wait_for_startup() {
  local pid="$1"
  local expected_script="$2"

  for _ in 1 2 3 4 5; do
    if kill -0 "${pid}" 2>/dev/null && pid_matches_script "${pid}" "${expected_script}"; then
      return 0
    fi

    sleep 0.2
  done

  return 1
}

wait_for_heartbeat() {
  local pid="$1"
  local expected_script="$2"
  local heartbeat_file="$3"

  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    if ! kill -0 "${pid}" 2>/dev/null || ! pid_matches_script "${pid}" "${expected_script}"; then
      return 1
    fi

    if [[ -f "${heartbeat_file}" ]]; then
      return 0
    fi

    sleep 0.2
  done

  return 1
}

stop_process() {
  local pid_file="$1"
  local expected_script="$2"

  if [[ ! -f "${pid_file}" ]]; then
    return 0
  fi

  local pid
  pid="$(<"${pid_file}")"

  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null || ! pid_matches_script "${pid}" "${expected_script}"; then
    rm -f "${pid_file}"
    return 0
  fi

  if ! kill "${pid}" 2>/dev/null; then
    printf 'failed to stop process for %s (pid=%s)\n' "${expected_script}" "${pid}" >&2
    return 1
  fi

  for _ in 1 2 3 4 5; do
    if ! kill -0 "${pid}" 2>/dev/null || ! pid_matches_script "${pid}" "${expected_script}"; then
      rm -f "${pid_file}"
      return 0
    fi

    sleep 0.2
  done

  printf 'failed to stop process for %s (pid=%s)\n' "${expected_script}" "${pid}" >&2
  return 1
}

start_process() {
  local name="$1"
  local python_bin="$2"
  local script_path="$3"
  local pid_file="$4"
  local log_file="$5"
  local heartbeat_file="$6"
  local heartbeat_env_name="$7"

  cleanup_stale_pid "${pid_file}" "${script_path}"

  local existing_pid
  existing_pid="$(find_running_pid_for_script "${script_path}" "${heartbeat_file}" | head -n 1)"
  if [[ -n "${existing_pid}" ]] && [[ ! -f "${pid_file}" ]]; then
    printf '%s already running without pid file (pid=%s)\n' "${name}" "${existing_pid}" >&2
    return 1
  fi

  if [[ -f "${pid_file}" ]]; then
    printf '%s already running (pid=%s)\n' "${name}" "$(<"${pid_file}")"
    return
  fi

  rm -f "${heartbeat_file}"

  (
    cd "${REPO_ROOT}"
    export REPO_ROOT="${REPO_ROOT}"
    export PYTHONPATH="${PYTHONPATH_VALUE}"
    export PATH="${JESSE_BIN_DIR}:${PATH}"
    export POSTGRES_HOST="${POSTGRES_HOST_VALUE}"
    export POSTGRES_PORT="${POSTGRES_PORT_VALUE}"
    export POSTGRES_DB="${POSTGRES_DB_VALUE}"
    export POSTGRES_USER="${POSTGRES_USER_VALUE}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD_VALUE}"
    export "${heartbeat_env_name}=${heartbeat_file}"

    "${python_bin}" "${script_path}" >>"${log_file}" 2>&1 &
    printf '%s' "$!" >"${pid_file}"
  )

  local pid
  pid="$(<"${pid_file}")"

  if ! wait_for_startup "${pid}" "${script_path}"; then
    rm -f "${pid_file}"
    printf 'failed to start %s; see %s\n' "${name}" "${log_file}" >&2
    return 1
  fi

  if ! wait_for_heartbeat "${pid}" "${script_path}" "${heartbeat_file}"; then
    rm -f "${pid_file}"
    printf 'failed to start %s; heartbeat not observed; see %s\n' "${name}" "${log_file}" >&2
    return 1
  fi

  printf 'started %s (pid=%s)\n' "${name}" "$(<"${pid_file}")"
}

if [[ "${DRYRUN_SKIP_PROCESS_START:-0}" == "1" ]]; then
  exit 0
fi

start_process \
  "executor" \
  "${EXECUTOR_PYTHON}" \
  "${EXECUTOR_SCRIPT_PATH}" \
  "${EXECUTOR_PID_FILE}" \
  "${EXECUTOR_LOG_FILE}" \
  "${EXECUTOR_HEARTBEAT_FILE}" \
  "EXECUTOR_HEARTBEAT_PATH"

if ! start_process \
  "jesse-dryrun" \
  "${JESSE_PYTHON}" \
  "${JESSE_SCRIPT_PATH}" \
  "${JESSE_PID_FILE}" \
  "${JESSE_LOG_FILE}" \
  "${JESSE_HEARTBEAT_FILE}" \
  "JESSE_HEARTBEAT_PATH"; then
  if ! stop_process "${EXECUTOR_PID_FILE}" "${EXECUTOR_SCRIPT_PATH}"; then
    printf 'rollback failed for executor\n' >&2
  fi
  exit 1
fi
