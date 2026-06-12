#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

echo "Running full Knowledge Workspace verification..."
"$venv_python" "$repo_root/scripts/verify_all.py" || {
  echo "Full verification failed. See the command output above." >&2
  exit 1
}
