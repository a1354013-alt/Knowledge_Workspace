#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$repo_root/backend"
frontend_dir="$repo_root/frontend"
venv_python="$repo_root/.venv311/bin/python"

if [[ ! -x "$venv_python" ]]; then
  echo "Missing .venv311. Run bash scripts/bootstrap-dev.sh first." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found. Install Node.js 20 LTS or newer, then run bash scripts/bootstrap-dev.sh." >&2
  exit 1
fi

backend_pid=""
frontend_pid=""

cleanup() {
  if [[ -n "${backend_pid:-}" ]] && kill -0 "$backend_pid" >/dev/null 2>&1; then
    kill "$backend_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "${frontend_pid:-}" ]] && kill -0 "$frontend_pid" >/dev/null 2>&1; then
    kill "$frontend_pid" >/dev/null 2>&1 || true
  fi
  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Knowledge Workspace development servers..."
echo "Backend API: http://127.0.0.1:8000"
echo "API Docs:    http://127.0.0.1:8000/docs"
echo "Frontend:    http://127.0.0.1:5173"
echo "Press Ctrl+C to stop both services."

(cd "$backend_dir" && "$venv_python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
backend_pid=$!

(cd "$frontend_dir" && npm run dev -- --host 127.0.0.1 --port 5173) &
frontend_pid=$!

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
