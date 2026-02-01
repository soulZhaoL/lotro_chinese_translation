#!/usr/bin/env bash
#
#./server/start_dev.sh --env .env 
#
set -euo pipefail

if [[ "${1:-}" == "--env" ]]; then
  if [[ -z "${2:-}" ]]; then
    echo "[ERROR] --env 参数缺少路径" >&2
    exit 1
  fi
  export LOTRO_ENV_PATH="$2"
  shift 2
fi

if [[ -n "${LOTRO_ENV_PATH:-}" ]]; then
  if [[ ! -f "${LOTRO_ENV_PATH}" ]]; then
    echo "[ERROR] 环境文件不存在: ${LOTRO_ENV_PATH}" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "${LOTRO_ENV_PATH}"
fi

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "[ERROR] 缺少环境变量: ${name}" >&2
    echo "[HINT] 请先 export ${name}=...，或用 --env /abs/path/to/.env" >&2
    exit 1
  fi
}

require_env LOTRO_SSH_HOST
require_env LOTRO_SSH_USER
require_env LOTRO_SSH_PORT
require_env LOTRO_TUNNEL_PORT
require_env LOTRO_REMOTE_DB_HOST
require_env LOTRO_REMOTE_DB_PORT
require_env LOTRO_BACKEND_HOST
require_env LOTRO_BACKEND_PORT

SSH_HOST="${LOTRO_SSH_HOST}"
SSH_USER="${LOTRO_SSH_USER}"
SSH_PORT="${LOTRO_SSH_PORT}"
LOCAL_PORT="${LOTRO_TUNNEL_PORT}"
REMOTE_DB_HOST="${LOTRO_REMOTE_DB_HOST}"
REMOTE_DB_PORT="${LOTRO_REMOTE_DB_PORT}"
BACKEND_HOST="${LOTRO_BACKEND_HOST}"
BACKEND_PORT="${LOTRO_BACKEND_PORT}"

echo "[INFO] 准备启动 SSH 隧道与后端服务"

if ! command -v ssh >/dev/null 2>&1; then
  echo "[ERROR] 未找到 ssh 命令，请先安装 OpenSSH" >&2
  exit 1
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "[ERROR] 未找到 uvicorn，请先激活虚拟环境并安装依赖" >&2
  exit 1
fi

if lsof -iTCP:"${LOCAL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[ERROR] 本地端口 ${LOCAL_PORT} 已被占用，请关闭占用或更换 LOTRO_TUNNEL_PORT" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${SSH_PID:-}" ]]; then
    kill "${SSH_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${SSH_LOG:-}" && -f "${SSH_LOG}" ]]; then
    rm -f "${SSH_LOG}"
  fi
}
trap cleanup EXIT INT TERM

echo "[INFO] 启动隧道: ${SSH_USER}@${SSH_HOST}:${SSH_PORT} -> 127.0.0.1:${LOCAL_PORT} -> ${REMOTE_DB_HOST}:${REMOTE_DB_PORT}"
SSH_LOG="$(mktemp -t tmp_ssh_tunnel)"
if ! ssh -f -N -L "${LOCAL_PORT}:${REMOTE_DB_HOST}:${REMOTE_DB_PORT}" \
  -o ExitOnForwardFailure=yes \
  -p "${SSH_PORT}" \
  "${SSH_USER}@${SSH_HOST}" 2>"${SSH_LOG}"; then
  echo "[ERROR] SSH 隧道启动失败，请检查账号/密码/网络" >&2
  if [[ -s "${SSH_LOG}" ]]; then
    echo "[ERROR] SSH 输出:" >&2
    cat "${SSH_LOG}" >&2
  fi
  exit 1
fi

if ! lsof -iTCP:"${LOCAL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[ERROR] SSH 隧道未监听本地端口 ${LOCAL_PORT}" >&2
  if [[ -s "${SSH_LOG}" ]]; then
    echo "[ERROR] SSH 输出:" >&2
    cat "${SSH_LOG}" >&2
  fi
  exit 1
fi
SSH_PID="$(lsof -iTCP:"${LOCAL_PORT}" -sTCP:LISTEN -t | head -n 1)"
if [[ -z "${SSH_PID}" ]]; then
  echo "[ERROR] 无法获取 SSH 隧道进程 PID" >&2
  if [[ -s "${SSH_LOG}" ]]; then
    echo "[ERROR] SSH 输出:" >&2
    cat "${SSH_LOG}" >&2
  fi
  exit 1
fi

echo "[INFO] 启动后端服务: uvicorn server.app:app --host ${BACKEND_HOST} --port ${BACKEND_PORT}"
uvicorn server.app:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
