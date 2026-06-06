# Frontend Smoke Checklist

Use the automated browser smoke when Playwright browsers are installed:

```powershell
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

CI uses `npm run test:e2e:ci` after lint, typecheck, unit tests, and build.

Manual fallback:

1. Start the backend and frontend with `scripts/start-dev.ps1` or equivalent terminals.
2. Open `http://127.0.0.1:5173`.
3. Confirm the login screen renders and demo/owner credentials reach the workspace shell.
4. Visit each workspace tab and confirm no blank page or crash.
5. Click refresh controls for documents, photos, knowledge, logbook, AutoTest, and prompts.
6. Switch between `zh-TW` and `en`.
7. Reload the browser and confirm the restored session returns to the workspace.
8. Confirm the page at `1366x768` keeps body scrolling disabled and uses internal panels for overflow.
9. Logout and confirm the token-backed session returns to the login screen.
