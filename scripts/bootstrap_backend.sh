#!/usr/bin/env bash
set -euo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Knowledge Workspace backend bootstrap"

if command -v uv >/dev/null 2>&1; then
  echo "Using uv with Python ${PYTHON_VERSION}"
  uv python install "$PYTHON_VERSION"
  uv venv --python "$PYTHON_VERSION" .venv
  .venv/bin/python -m pip install --upgrade pip
  uv pip install -e ".[dev]"
else
  PYTHON_BIN="${PYTHON_BIN:-python3.11}"
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python 3.11 was not found. Install Python 3.11 or install uv, then rerun this script." >&2
    exit 1
  fi
  "$PYTHON_BIN" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e ".[dev]"
fi

VERSION="$("$ROOT/.venv/bin/python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")"
case "$VERSION" in
  3.11.*) ;;
  *) echo "Warning: created Python ${VERSION}. This project supports Python 3.11.x." >&2 ;;
esac

cat <<'EOF'

Next commands:
  source .venv/bin/activate
  python scripts/run_backend_checks.py
  python scripts/export_openapi.py
  cd frontend && npm run generate:api-types
  cd backend && python -m uvicorn app.main:app --reload
EOF
