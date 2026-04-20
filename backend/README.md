# Backend API

Prereqs: Python 3.11 (matches CI).

## Start

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
# Set at least: JWT_SECRET (min 32 chars) and DEFAULT_OWNER_PASSWORD
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Main endpoints

- `POST /api/login`
- `GET /api/me`
- `POST /api/docs/upload`
- `GET /api/docs`
- `PATCH /api/docs/{doc_id}`
- `DELETE /api/docs/{doc_id}`
- `GET /api/docs/{doc_id}/download`
- `POST /api/photos/upload`
- `GET /api/photos`
- `PATCH /api/photos/{photo_id}`
- `DELETE /api/photos/{photo_id}`
- `GET /api/photos/{photo_id}/download`
- `POST /api/qa`
- `POST /api/generate`
- `GET /api/knowledge/entries`
- `POST /api/knowledge/entries`
- `PATCH /api/knowledge/entries/{entry_id}`
- `GET /api/logbook/entries`
- `POST /api/logbook/entries`
- `PATCH /api/logbook/entries/{entry_id}`
- `POST /api/logbook/entries/{entry_id}/promote-to-knowledge`
- `POST /api/autotest/run`
- `GET /api/autotest/runs`
- `GET /api/autotest/runs/{run_id}`
- `GET /api/item-links?item_id=...`
- `POST /api/items/resolve`

## Contract rules

- Login, QA, generate, and knowledge/logbook create/update use JSON bodies
- File upload uses multipart form data
- Auth is handled only through bearer token dependency injection

## Tests

```bash
cd backend
python -m pytest
python tests/run_smoke.py
```
