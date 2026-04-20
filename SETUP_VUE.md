# Frontend Setup

Frontend lives in `frontend/` and expects the backend at `http://localhost:8000` by default.

## Install

```bash
cd frontend
npm ci
```

## Environment

Create `.env.local` only for local development if you need a different API origin:

```env
VITE_API_BASE=http://localhost:8000
```

## Commands

```bash
npm run dev -- --host 0.0.0.0 --port 5173
npm test
npm run typecheck
npm run build
```

## Notes

- All frontend API calls go through `src/api.ts`
- Token storage/restore/logout is centralized in `src/auth.js`
- App initialization state is centralized in `src/app-state.js`
- Saved prompts and AutoTest workflows use the same API client and auth flow as the main app
