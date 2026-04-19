#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_ZIP="${1:-"$ROOT_DIR/enterprise_ai_release.zip"}"

STAGE_DIR="$(mktemp -d)"
cleanup() { rm -rf "$STAGE_DIR"; }
trap cleanup EXIT

RELEASE_ROOT="$STAGE_DIR/enterprise_ai"
mkdir -p "$RELEASE_ROOT"

cp -R "$ROOT_DIR/backend" "$RELEASE_ROOT/"
cp -R "$ROOT_DIR/frontend" "$RELEASE_ROOT/"
cp -R "$ROOT_DIR/scripts" "$RELEASE_ROOT/"

cp "$ROOT_DIR/VERSION" "$RELEASE_ROOT/"
cp "$ROOT_DIR/start_backend.sh" "$RELEASE_ROOT/"
cp "$ROOT_DIR/start_frontend.sh" "$RELEASE_ROOT/"

cp "$ROOT_DIR/README.md" "$RELEASE_ROOT/"
cp "$ROOT_DIR/QUICK_START.md" "$RELEASE_ROOT/"
cp "$ROOT_DIR/DELIVERY_CHECKLIST.md" "$RELEASE_ROOT/"
cp "$ROOT_DIR/CHANGELOG.md" "$RELEASE_ROOT/"
cp "$ROOT_DIR/PROJECT_STRUCTURE.md" "$RELEASE_ROOT/"

# Build frontend for the release package (keep dist, exclude node_modules).
(
  cd "$RELEASE_ROOT/frontend"
  npm ci
  npm run build
)
rm -rf "$RELEASE_ROOT/frontend/node_modules" || true

# Exclusions (must not ship)
rm -rf "$RELEASE_ROOT/.git" || true
rm -rf "$RELEASE_ROOT/frontend/node_modules" || true
rm -rf "$RELEASE_ROOT/backend/uploads" "$RELEASE_ROOT/backend/photos" "$RELEASE_ROOT/backend/autotest_uploads" "$RELEASE_ROOT/backend/chroma_db" || true
rm -rf "$RELEASE_ROOT/backend/.pytest-tmp" "$RELEASE_ROOT/backend/.pytest_cache" "$RELEASE_ROOT/frontend/.vite" || true

find "$RELEASE_ROOT" -type f -name ".env" -delete || true
find "$RELEASE_ROOT" -type f -name "*.db" -delete || true
find "$RELEASE_ROOT" -type d -name "__pycache__" -prune -exec rm -rf {} + || true
find "$RELEASE_ROOT" -type d -name ".pytest_cache" -prune -exec rm -rf {} + || true
find "$RELEASE_ROOT" -type d -name ".mypy_cache" -prune -exec rm -rf {} + || true

python - <<PY
import os
import zipfile

src_root = r"""$RELEASE_ROOT"""
out_zip = r"""$OUT_ZIP"""

os.makedirs(os.path.dirname(out_zip) or ".", exist_ok=True)
if os.path.exists(out_zip):
    os.remove(out_zip)

with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "uploads", "photos", "autotest_uploads", "chroma_db", "__pycache__", ".pytest_cache", ".mypy_cache", ".vite"}]
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, os.path.dirname(src_root))
            if name == ".env":
                continue
            if name.endswith(".db"):
                continue
            zf.write(path, rel)

print(f"Wrote release zip: {out_zip}")
PY
