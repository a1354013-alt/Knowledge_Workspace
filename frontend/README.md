# Frontend Overview

This folder contains the only supported frontend delivery tree.

## Commands

```bash
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
npm test
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

## Architecture

- `src/api.ts`: single API entrypoint (axios client + typed helpers returning `data`)
- `src/auth.ts`: token storage, restore, clear, unauthorized event flow
- `src/app-state.ts`: default app state helpers
- `src/App.vue`: login, token restore, documents, QA, templates
- `src/components/AutoTestPanel.vue`: project acceptance runs + knowledge capture hooks

Browser smoke coverage lives in `e2e/` and uses Playwright with mocked backend responses for login, tab navigation, refresh, locale switching, reload, body-scroll containment, and logout. CI runs it with `npm run test:e2e:ci`.
