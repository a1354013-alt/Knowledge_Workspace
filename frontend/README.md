# Frontend Overview

This folder contains the only supported frontend delivery tree.

## Commands

```bash
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
npm test
npm run typecheck
npm run build
```

## Architecture

- `src/api.ts`: single axios client and response handling (official API layer)
- `src/auth.js`: token storage, restore, clear, unauthorized event flow
- `src/app-state.js`: default app state helpers
- `src/App.vue`: login, token restore, documents, QA, templates
- `src/components/AutoTestPanel.vue`: project acceptance runs + knowledge capture hooks
