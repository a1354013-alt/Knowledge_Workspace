# Architecture Decisions (Knowledge Workspace)

This document captures the **intentional** trade-offs behind the current design so a reviewer can quickly understand what the project optimizes for, what boundaries exist, and what is explicitly out-of-scope.

## 1) Single-process, local-first architecture

**Decision:** Run as a single FastAPI backend + a Vite/Vue frontend, optimized for local usage and easy demo/repro.

**Why:**
- Low setup cost: no external DB or queue required.
- Works well as a portfolio repo: reviewers can run it quickly and understand the whole system in one sitting.

**Boundary / limitation:**
- Not designed for multi-tenant, multi-role enterprise authorization. Current auth is intentionally minimal and “owner” oriented.

## 2) Storage: SQLite for system-of-record + Chroma for retrieval

**Decision:** Use SQLite as the source of truth for structured entities, and Chroma as an auxiliary index for semantic/keyword retrieval.

**Why:**
- SQLite keeps the data model explicit, migratable, and testable without infrastructure.
- Retrieval index is treated as **derivative** data that can be rebuilt (best-effort) from SQLite.

**Boundary / limitation:**
- Vector index availability is an operational concern; when retrieval is unavailable, the system must **return an explicit status** (no silent success).

## 3) API contract: Pydantic “extra=forbid” and stable shapes

**Decision:** Backend request/response schemas are strict (Pydantic `extra="forbid"`) and the frontend types must match backend payloads.

**Why:**
- Avoid “frontend tolerates random backend shapes” which destroys delivery confidence.
- Enables high-value contract tests and predictable UI behavior.

**Boundary / limitation:**
- Contract changes require coordinated updates (backend schema + frontend types + tests).

## 4) AutoTest execution modes: simulated vs real

**Decision:** AutoTest supports two execution modes:
- `simulated`: deterministic, safe, CI-friendly; used for demos and default CI.
- `real`: runs project commands in a controlled working directory with hard limits.

**Why:**
- Demonstrates the product workflow without requiring external services.
- Keeps CI stable while still preserving a real-mode pathway.

**Boundary / limitation:**
- `real` mode must enforce safety boundaries (max files, max unzipped bytes, timeouts, skip logic) and must never silently downgrade to “LLM succeeded”.

## 5) OCR and LLM providers: capability surfaced explicitly

**Decision:** OCR and LLM integrations report health/availability via API; the UI should surface “available/healthy/fallback” states.

**Why:**
- Avoids misleading demos where advanced features appear to work but are actually running in noop/fallback.

**Boundary / limitation:**
- OCR requires a runnable system Tesseract binary in addition to Python deps; the backend status API is the source of truth.

