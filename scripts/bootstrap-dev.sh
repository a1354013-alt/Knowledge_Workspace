#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="$repo_root/.venv311"
venv_python="$venv_path/bin/python"
frontend_dir="$repo_root/frontend"
root_env="$repo_root/.env"
backend_env="$repo_root/backend/.env"

fail() {
  echo "Bootstrap failed: $*" >&2
  exit 1
}

find_python311() {
  for candidate in python3.11 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

new_secret() {
  "$python_cmd" - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

write_root_env_if_missing() {
  if [[ -f "$root_env" ]]; then
    echo ".env already exists; leaving it unchanged."
    return
  fi
  local secret
  secret="$(new_secret)"
  cat > "$root_env" <<EOF
# Backend runtime
JWT_SECRET=$secret
DEFAULT_OWNER_PASSWORD=ChangeMe123!
DATABASE_PATH=backend/documents.db
UPLOAD_DIR=backend/uploads
PHOTO_DIR=backend/photos
CHROMA_DB_PATH=backend/chroma_db

# AutoTest is simulated by default. Real command execution requires both flags.
AUTOTEST_MODE=simulated
KW_AUTOTEST_REAL_MODE=0
AUTOTEST_STALE_RUN_MINUTES=30

# LLM provider
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
EOF
  echo "Created .env with safe local defaults."
}

write_backend_env_if_missing() {
  if [[ -f "$backend_env" ]]; then
    echo "backend/.env already exists; leaving it unchanged."
    return
  fi
  local secret
  secret="$(new_secret)"
  cat > "$backend_env" <<EOF
JWT_SECRET=$secret
DEFAULT_OWNER_PASSWORD=ChangeMe123!
ALLOWED_ORIGINS=http://localhost:5173
DATABASE_PATH=documents.db
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800
PHOTO_DIR=./photos
CHROMA_DB_PATH=./chroma_db
AUTOTEST_DIR=./autotest_uploads
AUTOTEST_MODE=simulated
KW_AUTOTEST_REAL_MODE=0
AUTOTEST_TIMEOUT_SECONDS=120
AUTOTEST_MAX_FILES=500
AUTOTEST_MAX_UNZIPPED_BYTES=52428800
AUTOTEST_RLIMIT_CPU_SECONDS=30
AUTOTEST_RLIMIT_AS_MB=512
AUTOTEST_RLIMIT_FSIZE_MB=64
AUTOTEST_STALE_RUN_MINUTES=30
OCR_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
EOF
  echo "Created backend/.env with safe local defaults."
}

echo "Bootstrapping Knowledge Workspace with Python 3.11..."
python_cmd="$(find_python311)" || fail "Python 3.11 was not found. Install Python 3.11.x and retry."

"$python_cmd" -m venv "$venv_path" || fail "virtual environment creation failed"
[[ -x "$venv_python" ]] || fail "virtual environment was not created at $venv_path"

"$venv_python" -m pip install --upgrade pip || fail "pip upgrade failed"
"$venv_python" -m pip install -e "$repo_root[dev]" || fail "backend dev dependency installation failed"

command -v npm >/dev/null 2>&1 || fail "npm was not found. Install Node.js 20 LTS or newer and retry."
(cd "$frontend_dir" && npm ci) || fail "frontend dependency installation failed"

write_root_env_if_missing
write_backend_env_if_missing

echo
echo "Bootstrap complete."
echo "Next: bash scripts/start-dev.sh"
