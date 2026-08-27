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


---

# Phase 8.1 qo'shimchasi — cross-site cookie va CSRF

## Muammo

Production'da frontendlar Vercel'da, API Railway'da — bular **cross-site**. Oldingi
`SameSite=Strict` sozlamasida brauzer bunday so'rovlarda cookie'ni **umuman yubormaydi**,
ya'ni Seller Admin va Super Admin ishlamaydi.

## Cookie sozlamasi (konfiguratsiyadan, hardcoded emas)

| Muhit | `COOKIE_SAMESITE` | `COOKIE_SECURE` |
|---|---|---|
| Lokal | `lax` | `false` |
| Production | `none` | `true` |

Lokalda `localhost:3001` va `localhost:8000` — bir xil *site*, shuning uchun `lax` yetarli
va `Secure` shart emas (http). `SameSite=None` esa `Secure`siz brauzer tomonidan bekor
qilinadi, shuning uchun kod uni majburlaydi.

## CSRF — double-submit, sessiyaga bog'langan

`SameSite=Strict` bilvosita CSRF himoyasi bo'lgan edi. `None`ga o'tgach uni almashtirish
kerak:

```
csrf_token = HMAC-SHA256(CSRF_SECRET, sha256(session_token))
```

Ikkita cookie o'rnatiladi:

| Cookie | HttpOnly | Vazifa |
|---|:-:|---|
| `mp_session` / `mp_admin_session` | ✅ | Sessiya tokeni — JS o'qiy olmaydi |
| `mp_csrf` | ❌ | JS o'qib `X-CSRF-Token` header'iga qo'yadi |

### CSRF_SECRET — alohida secret

`CSRF_SECRET` boshqa hech qanday secret'dan olinmaydi. Xususan **`TELEGRAM_BOT_TOKEN`
hech qachon** CSRF signing key sifatida ishlatilmaydi:

- bot token'ni almashtirish (kompromis yoki oddiy rotatsiya) barcha faol sessiyalarning
  CSRF token'ini bekor qilib, foydalanuvchilarni tashqarida qoldirardi
- ikki xil vazifadagi secret'ni birlashtirish bittasining sizib chiqishi ta'sirini
  ikkinchisiga ham yoyadi

`APP_ENV=production` bo'lganda `CSRF_SECRET` **majburiy**: bo'lmasa ilova
`ValidationError` bilan ishga tushmaydi (`app/core/config.py` validator). Bu — jimgina
zaif himoya bilan ishlashdan ko'ra yaxshiroq.

Lokal va test muhitida `DEVELOPMENT_CSRF_SECRET` konstantasi ishlatiladi — u ochiq
matnda, ataylab "secret emas" deb nomlangan va production'da hech qachon ishlatilmaydi.

Yangi secret generatsiya qilish:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Nega token saqlanmaydi?** U sessiya tokenidan qayta hisoblanadi — DB'da ustun kerak
emas, migration kerak emas. Va u aynan bitta sessiyaga bog'langan: boshqa sessiyaning
token'i ishlamaydi (test bilan).

**Nega bu ishlaydi?** Hujumchi sayt `mp_csrf` cookie'sini **o'qiy olmaydi** (boshqa
origin, CORS ruxsat bermaydi), shuning uchun header'ni to'ldira olmaydi. Cookie
avtomatik yuborilsa ham, header'siz so'rov 403 oladi.

**Muhim:** faqat header hisobga olinadi. Cookie'ning o'zi hech narsani isbotlamaydi —
u cross-site so'rovda ham avtomatik ketadi.

## Qamrov

| So'rov | CSRF talab qilinadi |
|---|---|
| `GET`/`HEAD`/`OPTIONS` | ❌ |
| Bearer token bilan (Customer Mini App) | ❌ — header'ni cross-site qo'shib bo'lmaydi |
| Cookie bilan `POST`/`PATCH`/`PUT`/`DELETE` | ✅ |
| `/auth/telegram`, `/auth/telegram/seller`, `/admin/auth/login` | ❌ — sessiya hali yo'q |

Login endpointlari o'z credential'i bilan himoyalangan: Telegram imzosi yoki parol.

## Telegram'ning ikki xil imzosi

Telegram **ikki xil algoritm** ishlatadi va ular bir-birining payload'ini qabul qilmaydi:

| Sirt | Kalit | Funksiya |
|---|---|---|
| Mini App (`initData`) | `HMAC(bot_token, "WebAppData")` | `verify_init_data()` |
| Login Widget (brauzer) | `SHA256(bot_token)` | `verify_login_widget()` |

Ikkalasi alohida funksiyada saqlanadi — bir sirt uchun imzolangan payload ikkinchisida
**hech qachon** o'tmaydi (test bilan qamrab olingan).

Seller ikkala yo'l bilan ham kira oladi: brauzerda Login Widget, Telegram ichida Mini App.
Replay himoyasi ikkalasi uchun ham mavjud nonce mexanizmi orqali ishlaydi.
