# HBMS Backend

FastAPI backend for the Hotel Booking Management System.

## Quick Start

1. Install dependencies:
   - `uv sync --all-groups` (or `pip install -e ".[dev]"`)
2. Copy environment file:
   - `cp .env.example .env`
3. Run server:
   - `uvicorn hbms.main:app --reload --app-dir src`
4. Seed demo data:
   - `PYTHONPATH=src python -m hbms.scripts.seed`
5. Ingest hotel RAG PDF (section-aware chunking + `mistral-embed`):
   - Dry-run chunks: `uv run python -m hbms.scripts.ingest_hotel_pdf --dry-run`
   - Full ingest: `uv run python -m hbms.scripts.ingest_hotel_pdf --organization-id <org_id> --hotel-id <hotel_id>`

Set `MISTRAL_API_KEY` in `.env` before full ingest.

## Demo accounts

After seeding, all passwords are `Password123!`:

- `product.admin@hbms.example` — PRODUCT_ADMIN
- `org.admin@hbms.example` — ORG_ADMIN
- `receptionist@hbms.example` — RECEPTIONIST
- `customer@hbms.example` — CUSTOMER

## Quality

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run mypy src`
- Tests: `uv run pytest`
