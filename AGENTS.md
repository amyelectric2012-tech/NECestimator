# AGENTS.md — NECestimator

Residential electrical estimator (NEC 2017 Art. 220). Monorepo: FastAPI backend + React/Vite frontend, single deployable (FastAPI serves built bundle from `backend/static`).

## Commands

Backend (run from `backend/`):
- Tests: `python -m pytest -q` (51 tests). Single file: `python -m pytest tests/test_nec220.py -q`. Single test: `python -m pytest -k "test_name" -q`.
- Lint: `ruff check .` (`ruff check --fix .` to auto-fix). Config in `pyproject.toml` (line 120, py3.12; ignores B008/E501/BLE001).
- Migrations: `alembic upgrade head`; `alembic revision --autogenerate -m "..."`; `alembic current`. Run from `backend/` (prepend_sys_path=.).
- Seed (needed for demo/E2E): `python seed.py && python seed_examples.py` (materials/labor rates + demo user `demo@example.com` / `demo123`).
- Dev server: `uvicorn app.main:app --reload` (needs `DATABASE_URL`).

Frontend (run from `frontend/`):
- Dev: `npm run dev` (Vite, port 5173; API proxied to localhost:8000).
- Lint: `npm run lint` (oxlint).
- Build: `npm run build` (`tsc -b && vite build`).
- E2E: `npm run test:e2e` (Playwright). Config `playwright.config.ts`.

Docker: `docker-compose up --build` (API :8000). Dockerfile builds frontend then copies `dist` → `backend/static`.

## Environment

- `DATABASE_URL` — Postgres. Local dev DB runs on **port 5433** (container `estimator-db`); default config uses 5432.
- `SECRET_KEY` — JWT secret.
- `PDF_DIR` — generated PDFs (default `/tmp/estimator_pdfs`).
- `SMTP_HOST/PORT/USER/PASSWORD/FROM/TLS` — email delivery; endpoint fails if `SMTP_HOST` empty.
- Tests override `DATABASE_URL` to SQLite in-memory via `conftest.py` (no Postgres needed). `Base.metadata.create_all` creates schema.

## Architecture notes

- Two calc engines coexist — do not assume one:
  - `app/calculations/nec220.py` (dataclasses `ProjectInput`/`Appliance`/`HVAC`; `standard_method`, `optional_220_82/83/84`, `calculate_all`) — used by project `/calculate` and estimates.
  - `app/services/load_calc/` (pydantic `LoadCalcRequest`/`LoadCalcResult`, table-driven) — exposed via `/calculations` and `/api/v1/calculations`. Consolidation deferred.
- Takeoff `labor_hours` is stored **per unit**; summary multiplies `quantity × hours`. Keep this when editing generator.
- Frontend API base: `window.location.port === "5173" ? "http://localhost:8000" : ""` — relative in prod, absolute in dev.
- Plain CSS (not Tailwind) — user explicitly chose.
- bcrypt used directly (passlib/bcrypt 5 incompatibility avoided).
- List endpoints return `X-Total-Count` header (pagination via `limit`/`offset`).
- Security headers middleware + `robots.txt` (authenticated app). CORS allows all origins.
- All PDFs state "Preliminary — Not for Construction".
- NEC full text: `backend/data/nec_2017.txt`.

## Gotchas

- `backend/static/` and `frontend/dist/` are gitignored build artifacts; Docker builds them.
- `.venv` lives at repo root (README's `backend/.venv` is stale).
- Alembic head: `927fb1dc5e7a`. Run migrations from `backend/`.
- Demo credentials: `demo@example.com` / `demo123` (3 example projects).
- Chat commands: generate takeoff, calculate, summary, add, list, clear, `nec <q>`, `describe <work>`.
- `app/calculations/` still exists alongside `services/load_calc/`; check both before changing calc logic.
- SMTP/OpenAI keys not configured by default; email/LLM features require env vars.
- Do not hard-code client names or project data; never commit secrets.
