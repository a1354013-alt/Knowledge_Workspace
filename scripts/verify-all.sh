#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_python="$repo_root/.venv311/bin/python"

if [[ ! -x "$venv_python" ]]; then
  echo "Missing .venv311. Run bash scripts/bootstrap-dev.sh first." >&2
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
