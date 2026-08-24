# Development Phases

**Hozirgi faza: Phase 5 — Customer marketplace catalog**

- Phase 0 — Architecture ✅
- Phase 1 — Repository & Infrastructure ✅
- Phase 2 — Database (business schema, migrations) ✅
- Phase 3 — Authentication (Telegram initData, seller/admin auth) ✅
- Phase 4 — Multi-tenancy ✅ (Phase 3'da dependency darajasida, Phase 4'da repository darajasida)
- Phase 5 (rejada) — Seller Admin CRUD — Phase 4'da bajarildi ✅
- **Phase 6 (rejada) — Customer Mini App** — katalog/discovery qismi Phase 5'da bajarildi ⬅ hozir shu yerdamiz
- Phase 7 — Cart & Orders (checkout, server-side narx)
- Phase 8 — Telegram Notifications (bot worker, deep link)
- Phase 9 — Super Admin (shop boshqaruvi, statistika)
- Phase 10 — Subscription (tarif tizimi asosi, to'lovsiz)
- Phase 11 — Production hardening (RLS, rate limiting, monitoring, backup)

Har bir faza tugagach test qilinadi va alohida topshiriq bilan keyingisiga o'tiladi. Phase 2 — database schema va migrationlar. Authentication, API CRUD va UI hali yozilmagan.
