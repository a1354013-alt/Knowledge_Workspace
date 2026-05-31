#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="$repo_root/.venv311"
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

resolve_venv_python() {
  if [[ -x "$venv_path/bin/python" ]]; then
    printf '%s\n' "$venv_path/bin/python"
    return 0
  fi
  if [[ -x "$venv_path/Scripts/python.exe" ]]; then
    printf '%s\n' "$venv_path/Scripts/python.exe"
    return 0
  fi
  return 1
}

write_root_env_if_missing() {
  if [[ -f "$root_env" ]]; then
    normalize_utf8_bom_if_present "$root_env"
    echo ".env already exists; leaving it unchanged."
    return
  fi
  local secret
  secret="$(new_secret)"
  cat > "$root_env" <<EOF
# Backend runtime
JWT_SECRET=$secret
DEFAULT_OWNER_PASSWORD=ChangeMe123!
DATABASE_PATH=./documents.db
UPLOAD_DIR=./uploads
PHOTO_DIR=./photos
CHROMA_DB_PATH=./chroma_db

# AutoTest defaults to simulated execution; uploaded code does not run until explicitly enabled.
AUTOTEST_MODE=simulated
KW_AUTOTEST_REAL_MODE=0
KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=0
AUTOTEST_SANDBOX_BACKEND=disabled
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
    normalize_utf8_bom_if_present "$backend_env"
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
KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=0
AUTOTEST_SANDBOX_BACKEND=disabled
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

clean_packaging_artifacts() {
  find "$repo_root/backend" -maxdepth 1 \( -name "*.egg-info" -o -name "*.dist-info" \) -exec rm -rf {} +
}

normalize_utf8_bom_if_present() {
  local path="$1"
  [[ -f "$path" ]] || return 0
  "$python_cmd" - "$path" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
data = path.read_bytes()
prefix = b"\xef\xbb\xbf"
if data.startswith(prefix):
    path.write_bytes(data[len(prefix):])
    print(f"{path} had a UTF-8 BOM; normalized encoding without changing values.")
PY
}

echo "Bootstrapping Knowledge Workspace with Python 3.11..."
python_cmd="$(find_python311)" || fail "Python 3.11 was not found. Install Python 3.11.x and retry."

"$python_cmd" -m venv "$venv_path" || fail "virtual environment creation failed"
venv_python="$(resolve_venv_python)" || fail "virtual environment was not created at $venv_path"

"$venv_python" -m pip install --upgrade pip || fail "pip upgrade failed"
"$venv_python" -m pip install -e "$repo_root[dev]" || fail "backend dev dependency installation failed"
clean_packaging_artifacts

command -v npm >/dev/null 2>&1 || fail "npm was not found. Install Node.js 20 LTS or newer and retry."
(cd "$frontend_dir" && npm ci) || fail "frontend dependency installation failed"

write_root_env_if_missing
write_backend_env_if_missing

echo
echo "Bootstrap complete."
echo "Next: bash scripts/start-dev.sh"
