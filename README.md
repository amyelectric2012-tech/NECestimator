# Electrical Estimator (MVP)

Residential electrical estimating tool: NEC 2017 Article 220 load calculations (Standard + Optional methods), material takeoff, editable pricing, PDF bid generation, and searchable NEC reference.

## Stack
- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- Frontend: React + TypeScript + Vite
- PDF: ReportLab

## Run with Docker
```bash
docker-compose up --build
```
API at http://localhost:8000, docs at http://localhost:8000/docs.

## Run locally
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/estimator"
alembic upgrade head
python seed.py
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Environment variables
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret
- `PDF_DIR` - directory for generated PDFs (default /tmp/estimator_pdfs)

## Tests
```bash
cd backend && pytest -q
```

## API overview
- Auth: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- Projects: `POST/GET/PUT/DELETE /projects`, `POST /projects/{id}/calculate`, `GET /projects/{id}/load-calc`
- Materials: `/materials` CRUD
- Estimates/takeoff: `POST /projects/{id}/estimates`, `POST /projects/{id}/takeoff`
- PDF: `GET /projects/{id}/export-pdf`
- NEC reference: `GET /nec/search?q=`, `GET /nec/tables/{220.42,220.54,220.55,220.84}`

## Notes
- All calculations are preliminary and must be verified in the field.
- Every PDF states "Preliminary — Not for Construction".
- Residential only (single-family, multi-family, ADU).
