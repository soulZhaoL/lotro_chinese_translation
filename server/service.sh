#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 {start|stop|status|restart} --env /abs/path/.env" >&2
  exit 1
}

if [[ $# -lt 2 ]]; then
  usage
fi

CMD="$1"
shift

if [[ "${1:-}" != "--env" || -z "${2:-}" ]]; then
  usage
fi

ENV_PATH="$2"
if [[ ! -f "${ENV_PATH}" ]]; then
  echo "[ERROR] 环境文件不存在: ${ENV_PATH}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_PATH}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "[ERROR] 缺少环境变量: ${name}" >&2
    exit 1
  fi
}

require_env LOTRO_BACKEND_HOST
require_env LOTRO_BACKEND_PORT
require_env LOTRO_PID_PATH
require_env LOTRO_LOG_PATH

PID_PATH="${LOTRO_PID_PATH}"
LOG_PATH="${LOTRO_LOG_PATH}"

ensure_parent_dir() {
  local file_path="$1"
  if [[ -d "${file_path}" ]]; then
    echo "[ERROR] 路径应为文件，但给的是目录: ${file_path}" >&2
    exit 1
  fi
  local parent_dir
  parent_dir="$(dirname "${file_path}")"
  if [[ -e "${parent_dir}" && ! -d "${parent_dir}" ]]; then
    echo "[ERROR] 父路径不是目录: ${parent_dir}" >&2
    exit 1
  fi
  if [[ ! -d "${parent_dir}" ]]; then
    mkdir -p "${parent_dir}"
  fi
}

ensure_parent_dir "${PID_PATH}"
ensure_parent_dir "${LOG_PATH}"

is_running() {
  if [[ -f "${PID_PATH}" ]]; then
    local pid
    pid="$(cat "${PID_PATH}")"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start_service() {
  if is_running; then
    echo "[INFO] 服务已在运行 (PID: $(cat "${PID_PATH}"))"
    exit 0
  fi
  if [[ -f "${PID_PATH}" ]]; then
    rm -f "${PID_PATH}"
  fi
  nohup uvicorn server.app:app --host "${LOTRO_BACKEND_HOST}" --port "${LOTRO_BACKEND_PORT}" \
    >> "${LOG_PATH}" 2>&1 &
  echo $! > "${PID_PATH}"
  echo "[INFO] 已启动 (PID: $(cat "${PID_PATH}"))"
}

stop_service() {
  if ! is_running; then
    echo "[INFO] 服务未运行"
    exit 0
  fi
  local pid
  pid="$(cat "${PID_PATH}")"
  kill "${pid}"
  echo "[INFO] 已发送停止信号 (PID: ${pid})"
}

status_service() {
  if is_running; then
    echo "[INFO] 运行中 (PID: $(cat "${PID_PATH}"))"
    exit 0
  fi
  echo "[INFO] 未运行"
}

case "${CMD}" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  status)
    status_service
    ;;
  restart)
    stop_service
    sleep 1
    start_service
    ;;
  *)
    usage
    ;;
esac
