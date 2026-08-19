# Architecture — qisqa, amaliy versiya

To'liq tahlil (barcha bo'limlar, trade-off'lar, database schema tafsilotlari) — arxitektura tasdiqlash bosqichidagi hujjatda. Bu fayl — kunlik ishda tez ma'lumot uchun qisqartirilgan versiya.

## Tech stack

- Backend: FastAPI (Python 3.12), SQLAlchemy 2.x (async), Alembic, Pydantic v2, asyncpg
- Frontend: Next.js + TypeScript (3 alohida app: customer-app, seller-admin, super-admin)
- Database: PostgreSQL
- Object storage: Cloudflare R2
- Hosting: Railway (backend + bot + Postgres), Vercel (frontendlar)
- Bot: Telegram Bot API (aiogram) — alohida Railway service, keyingi fazada

## Multi-tenancy

- Kalit: `shop_id`
- Seller so'rovlarida `shop_id` — token'dan (JWT/session), hech qachon request body/query'dan emas
- Repository layer funksiyalari `shop_id`ni majburiy parametr sifatida qabul qiladi
- RLS (PostgreSQL Row-Level Security) — Phase 11'da qo'shimcha himoya qatlami sifatida

## Order modeli

Har shop uchun alohida order (bitta customer bir nechta shopdan xarid qilsa, har biri uchun alohida order). Customer — global akkaunt (bir nechta shopda xarid qilishi mumkin).

## Auth

- Customer: Telegram initData HMAC verification → JWT (Mini App uchun)
- Seller/Super Admin: httpOnly secure session cookie + CSRF himoya

## Monorepo

```
apps/api            FastAPI backend
apps/customer-app    Telegram Mini App
apps/seller-admin    Seller paneli
apps/super-admin     Platforma boshqaruvi
packages/shared      Umumiy type/config
```

## Fazalar

Batafsil — `docs/development-phases.md`.
