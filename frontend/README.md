# HBMS Frontend

React + Vite + TypeScript + SCSS UI for the Hotel Booking Management System.

## Run

```bash
npm install
npm run dev
```

App: `http://127.0.0.1:5173`  
API proxy: `/api` → `http://127.0.0.1:8000`

## Demo logins

Password for all seeded users: `Password123!`

- `customer@hbms.example`
- `receptionist@hbms.example`
- `org.admin@hbms.example`
- `product.admin@hbms.example`

## Structure

- `src/styles` — design tokens + global styles
- `src/components/ui` — reusable design-system primitives
- `src/components/domain` — shared booking/room components
- `src/components/layout` — app/auth shells
- `src/pages` — thin route pages composing shared components
