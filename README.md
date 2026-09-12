# HBMS — Arohak

Hotel Booking Management System with multi-tenant orgs, role-based auth, room search & bookings, staff dashboards, and an AI hotel-info chat (RAG over PDF).

## Stack

- **Backend:** Python, FastAPI, MongoDB, JWT auth, Mistral (RAG)
- **Frontend:** React, Vite, TypeScript, SCSS

## Setup

### Backend

```bash
cd backend
uv sync --all-groups
cp .env.example .env   # set MONGODB_URI, JWT_SECRET_KEY, MISTRAL_API_KEY
uvicorn hbms.main:app --reload --app-dir src
PYTHONPATH=src python -m hbms.scripts.seed
```

API: `http://127.0.0.1:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: `http://127.0.0.1:5173` (proxies `/api` → backend)

## Demo accounts

After seeding, password for all users: `Password123!`

| Email | Role |
|---|---|
| `customer@hbms.example` | CUSTOMER |
| `receptionist@hbms.example` | RECEPTIONIST |
| `org.admin@hbms.example` | ORG_ADMIN |
| `product.admin@hbms.example` | PRODUCT_ADMIN |
