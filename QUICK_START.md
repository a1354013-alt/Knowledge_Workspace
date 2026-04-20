# Quick Start

Prereqs: Python 3.11 (matches CI) and Node.js 20.

## 1. Install backend

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
```

Set at least:

- `JWT_SECRET` (min 32 characters)
- `DEFAULT_OWNER_PASSWORD`
- `ALLOWED_ORIGINS=http://localhost:5173`

## 2. Start backend

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 3. Install frontend

```bash
cd ../frontend
npm ci
```

## 4. Start frontend

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

## 5. Verify

- Open `http://localhost:5173`
- Log in with `owner` and the password from `backend/.env`
- Upload a document
- Ask a QA question
- Run `python scripts/smoke_check.py --password "<owner password>"`

Optional (recommended) validation:

```bash
cd frontend
npm test
npm run typecheck
npm run build
```
