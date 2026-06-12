#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$repo_root/backend"
frontend_dir="$repo_root/frontend"

resolve_venv_python() {
  if [[ -x "$repo_root/.venv/bin/python" ]]; then
    printf '%s\n' "$repo_root/.venv/bin/python"
    return 0
  fi
  if [[ -x "$repo_root/.venv/Scripts/python.exe" ]]; then
    printf '%s\n' "$repo_root/.venv/Scripts/python.exe"
    return 0
  fi
  return 1
}

if ! venv_python="$(resolve_venv_python)"; then
  echo "Missing .venv. Run bash scripts/bootstrap-dev.sh first." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found. Install Node.js 20 LTS or newer, then run bash scripts/bootstrap-dev.sh." >&2
  exit 1
fi

load_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 0
  local line key value
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line//$'\r'/}"
    line="${line#$'\xef\xbb\xbf'}"
    [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key//[[:space:]]/}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    export "$key=$value"
  done < "$env_file"
}

backend_pid=""
frontend_pid=""

terminate_group() {
  local pid="${1:-}"
  [[ -z "$pid" ]] && return 0
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 0
  fi
  kill -TERM "-$pid" >/dev/null 2>&1 || kill "$pid" >/dev/null 2>&1 || true
}

cleanup() {
  trap - EXIT INT TERM
  terminate_group "$backend_pid"
  terminate_group "$frontend_pid"
  sleep 1
  [[ -n "${backend_pid:-}" ]] && kill -KILL "-$backend_pid" >/dev/null 2>&1 || true
  [[ -n "${frontend_pid:-}" ]] && kill -KILL "-$frontend_pid" >/dev/null 2>&1 || true
  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

start_in_process_group() {
  if command -v setsid >/dev/null 2>&1; then
    setsid bash -c "$1" &
  else
    bash -c "$1" &
  fi
  started_pid="$!"
}

echo "Starting Knowledge Workspace development servers..."
echo "Backend API: http://127.0.0.1:8000"
echo "API Docs:    http://127.0.0.1:8000/docs"
echo "Frontend:    http://127.0.0.1:5173"
echo "Press Ctrl+C to stop both services."

started_pid=""
start_in_process_group "cd '$backend_dir' && $(declare -f load_env_file) && load_env_file .env && '$venv_python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
backend_pid="$started_pid"
start_in_process_group "cd '$frontend_dir' && npm run dev -- --host 127.0.0.1 --port 5173"
frontend_pid="$started_pid"

while true; do
  if ! kill -0 "$backend_pid" >/dev/null 2>&1; then
    set +e
    wait "$backend_pid"
    exit_code=$?
    set -e
    echo "Backend server exited with code $exit_code." >&2
    exit "$exit_code"
  fi
  if ! kill -0 "$frontend_pid" >/dev/null 2>&1; then
    set +e
    wait "$frontend_pid"
    exit_code=$?
    set -e
    echo "Frontend server exited with code $exit_code." >&2
    exit "$exit_code"
  fi
  sleep 1
done
