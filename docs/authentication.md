# Authentication & Identity (Phase 3)

## Uch xil realm — aralashmaydi

| Realm | Kim | Qanday kiradi | Sessiya |
|---|---|---|---|
| `customer` | Xaridor | Telegram Mini App initData | Bearer token (xotirada) |
| `seller` | Do'kon xodimi | Telegram + `shop_members` | httpOnly cookie |
| `platform_admin` | Platforma egasi | Email + parol | httpOnly cookie |

Sessiyada `principal_type` saqlanadi va har bir dependency uni tekshiradi — customer tokeni
admin endpointiga o'tmaydi (test bilan qamrab olingan).

## Telegram initData verifikatsiyasi

`app/services/telegram_auth.py` — Telegram'ning rasmiy algoritmi: `HMAC-SHA256(bot_token)` bilan
kalit chiqariladi, `data_check_string` alifbo tartibida yig'iladi, `hmac.compare_digest` bilan
solishtiriladi (timing-safe). Bot token faqat serverda, frontendga hech qachon chiqmaydi.

Qo'shimcha tekshiruvlar: `auth_date` eskirganmi (default 300s), kelajakdan kelganmi (soat
manipulyatsiyasi), `user` payload to'g'rimi.

**Replay himoyasi:** har qabul qilingan initData'ning SHA-256'i `telegram_auth_nonces` jadvaliga
unique constraint bilan yoziladi. Bir xil payload ikkinchi marta kelsa — 401. Eskirgan yozuvlar
har chaqiruvda tozalanadi (alohida cron kerak emas).

## Sessiya strategiyasi — nega JWT emas

Server tomonda saqlanadigan **opaque token** tanlandi:

- **Bekor qilinadi.** JWT bekor qilib bo'lmaydi (muddati tugagunicha amal qiladi). Seller'ni
  shopdan chiqarganda yoki admin akkaunt buzilganda sessiya darhol o'ldirilishi kerak.
- **DB'da faqat SHA-256 digest saqlanadi** — baza sizib chiqsa ham tokenlar ishlatib bo'lmaydi.
- **Membership har so'rovda qayta o'qiladi** — JWT ichidagi `shop_id`ga ishonib qolinmaydi.

Cookie'lar: `httpOnly`, `Secure`, `SameSite=Strict`, cheklangan `max_age`. `SameSite=Strict`
CSRF'ning asosiy vektorini yopadi.

Customer Mini App uchun cookie emas, **bearer token xotirada** — Telegram WebView'da cross-site
cookie ishonchsiz. `localStorage` ishlatilmaydi (XSS'da o'g'irlanadi).

## Tenant context — eng muhim qism

```
session (server-side)
  → user_id + shop_id
    → shop_members qayta tekshiriladi (har so'rovda)
      → get_current_shop_id()
        → service / repository
```

Frontend yuborgan `shop_id` **faqat kandidat**: `POST /auth/telegram/seller` uni qabul qiladi,
lekin membership topilmasa 403 qaytaradi. Endpointlar `shop_id`ni requestdan olmaydi.

## RBAC

`OWNER ⊃ ADMIN ⊃ MANAGER`. Ruxsatlar `app/core/rbac.py`da permission sifatida e'lon qilingan
(`product:write`, `order:update`, `shop:member:manage`, ...), shuning uchun keyingi fazalarda
endpointlar rolga emas, permission'ga bog'lanadi: `Depends(require_permission(Permission.X))`.

## Brute-force

Super Admin: 5 ta noto'g'ri urinishdan keyin 15 daqiqa blok (`locked_until`). Mavjud bo'lmagan
email uchun ham parol tekshiruvi bajariladi — javob akkaunt bor-yo'qligini oshkor qilmaydi.

Telegram realm'ida parol yo'q, shuning uchun brute-force o'rniga replay + expiry himoyasi ishlaydi.

## Keyinchalik

- **TOTP 2FA:** `platform_admins.totp_secret` ustuni tayyor, faqat verifikatsiya qadami qo'shiladi
- **Rate limiting:** hozircha ilova darajasida (login lockout). Umumiy IP-based rate limiting
  Phase 11'da qo'shiladi; agar bir nechta instance bo'lsa, o'shanda Redis kerak bo'ladi —
  hozircha MVP uchun ortiqcha infratuzilma
