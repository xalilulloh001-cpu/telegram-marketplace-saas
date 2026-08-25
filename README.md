# Telegram Multi-Tenant Marketplace SaaS

## Project

Telegram ichida ishlaydigan ko'p-sotuvchili (multi-tenant) marketplace SaaS platformasi. Har bir seller o'z Telegram Mini App do'koniga ega bo'ladi, barcha do'konlar bitta umumiy backend orqali ishlaydi. To'liq arxitektura — `docs/architecture.md`.

## Architecture

```
Customer Mini App     Seller Admin     Super Admin
        \                  |                /
         \                 |               /
                       FastAPI (api)
                            |
                       PostgreSQL
```

Telegram bot — alohida worker (`apps/bot`, keyingi fazada qo'shiladi).

## Local development

### Backend (`apps/api`)

```bash
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env   # DATABASE_URL'ni to'g'irlang, kerak bo'lsa
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

`GET /api/v1/health` → `{"status": "ok"}`

### Frontendlar

Har biri mustaqil Next.js app:

```bash
cd apps/customer-app   # yoki seller-admin, super-admin
npm install
cp .env.example .env.local
npm run dev
```

Portlar: `customer-app` → 3000, `seller-admin` → 3001, `super-admin` → 3002.

### PostgreSQL (Docker orqali)

```bash
docker compose up -d postgres
```

Yoki butun backend+DB'ni birga: `docker compose up`.

## Environment variables

Har bir app o'zining `.env.example` fayliga ega (`apps/api/.env.example`, `apps/customer-app/.env.example`, va h.k.). `.env` fayllar hech qachon repo'ga commit qilinmaydi.

## Project structure

```
apps/
  api/             FastAPI backend
  customer-app/    Telegram Mini App (Next.js)
  seller-admin/    Seller boshqaruv paneli (Next.js)
  super-admin/     Platforma boshqaruv paneli (Next.js)
packages/
  shared/          Frontendlar orasida umumiy type/config uchun asos
infrastructure/    Deployment-bilan bog'liq konfiguratsiya
docs/              Arxitektura va development-phases hujjatlari
```

## Current phase

> Phase 7 — Checkout & Orders

Barcha fazalar — `docs/development-phases.md`.
