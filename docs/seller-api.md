# Seller API (Phase 4)

## Konventsiyalar

| Holat | Kod |
|---|---|
| GET / PATCH | 200 |
| POST | 201 |
| DELETE | 204 |
| Validatsiya xatosi | 422 |
| Autentifikatsiyasiz | 401 |
| Ruxsat yetarli emas | 403 |
| Topilmadi **yoki boshqa shopga tegishli** | 404 |
| Biznes qoidasi buzildi (mavjud, o'chirib bo'lmaydi) | 409 |

**Nega 404, 403 emas?** Agar boshqa shopning mahsulotiga 403 qaytarsak, bu "bunday ID mavjud"
degan ma'lumotni oshkor qiladi. 404 esa "yo'q" deydi — seller boshqa shoplarning ID diapazonini
skanerlab, ular haqida hech narsa bilib ololmaydi. Bu pattern butun API bo'ylab izchil.

## Endpointlar

```
GET    /api/v1/seller/shop
PATCH  /api/v1/seller/shop                         SHOP_SETTINGS_WRITE

GET    /api/v1/seller/shop/members                 MEMBER_VIEW
POST   /api/v1/seller/shop/members                 MEMBER_MANAGE
PATCH  /api/v1/seller/shop/members/{id}            MEMBER_MANAGE
DELETE /api/v1/seller/shop/members/{id}            MEMBER_MANAGE

GET    /api/v1/seller/categories                   PRODUCT_VIEW
POST   /api/v1/seller/categories                   CATEGORY_WRITE
GET    /api/v1/seller/categories/{id}              PRODUCT_VIEW
PATCH  /api/v1/seller/categories/{id}              CATEGORY_WRITE
DELETE /api/v1/seller/categories/{id}              CATEGORY_WRITE

GET    /api/v1/seller/products                     PRODUCT_VIEW
POST   /api/v1/seller/products                     PRODUCT_WRITE
GET    /api/v1/seller/products/{id}                PRODUCT_VIEW
PATCH  /api/v1/seller/products/{id}                PRODUCT_WRITE
DELETE /api/v1/seller/products/{id}                PRODUCT_WRITE

GET    /api/v1/seller/products/{id}/images         PRODUCT_VIEW
POST   /api/v1/seller/products/{id}/images         PRODUCT_WRITE
PATCH  /api/v1/seller/products/{id}/images/{img}   PRODUCT_WRITE
DELETE /api/v1/seller/products/{id}/images/{img}   PRODUCT_WRITE
```

## RBAC matritsasi

| Permission | OWNER | ADMIN | MANAGER |
|---|:-:|:-:|:-:|
| product:view / product:write | ✅ | ✅ | ✅ |
| category:write | ✅ | ✅ | ✅ |
| order:view / order:update | ✅ | ✅ | ✅ |
| customer:view | ✅ | ✅ | ✅ |
| discount:write | ✅ | ✅ | — |
| shop:settings:write | ✅ | ✅ | — |
| shop:member:view | ✅ | ✅ | — |
| shop:member:manage | ✅ | — | — |
| shop:subscription:manage | ✅ | — | — |

Endpointlar rolni emas, permission'ni tekshiradi: `Depends(require_permission(Permission.X))`.

## Tenant isolation

`shop_id` **hech qachon** request body yoki query'dan olinmaydi — faqat sessiyadan
(`get_current_shop_id`). Repository funksiyalarida `shop_id` majburiy argument, ya'ni
uni unutib qoldiradigan kod yo'li mavjud emas.

Body'da `shop_id` yuborilsa — e'tiborsiz qoldiriladi (Pydantic schema'da bunday maydon yo'q).

## Pagination

```
?page=1&page_size=20      # page_size: 1..100, default 20
```

```json
{ "items": [], "page": 1, "page_size": 20, "total": 100, "pages": 5 }
```

## Filter va sorting

```
?search=iphone&category_id=3&is_active=true&sort=price_asc
```

`sort` — yopiq ro'yxat (`newest`, `oldest`, `price_asc`, `price_desc`, `name_asc`, `name_desc`).
Noma'lum qiymat 422 oladi va SQL'ga yetib bormaydi.

## Slug

Slug **serverda** nomdan generatsiya qilinadi, klientdan qabul qilinmaydi. Unikallik
shop ichida (`UNIQUE(shop_id, slug)`) — ikki shop bir xil slug ishlatishi mumkin. Takrorlansa
avtomatik `-2`, `-3` qo'shiladi.

## Category o'chirish — RESTRICT

Kategoriyada mahsulot yoki ichki kategoriya bo'lsa, o'chirish 409 qaytaradi. Shu tufayli
hech bir mahsulot tasodifan kategoriyasiz qolmaydi.

## Rasm saqlash

```
Seller API → ObjectStorage → Cloudflare R2 (yoki InMemory adapter)
```

Kalit formati tenant-aware: `shops/{shop_id}/products/{product_id}/{uuid}.{ext}` — shoplar
o'rtasida to'qnashuv bo'lmaydi.

Validatsiya: MIME turi (`jpeg`/`png`/`webp`), hajm ≤ 5MB. **Kengaytma MIME turidan olinadi,
yuklangan fayl nomidan emas** — `evil.php.jpg` kabi nom hech narsa bermaydi. URL ham serverda
yasaladi, klient yuborgan URL saqlanmaydi.

R2 credentiallari bo'lmasa `InMemoryStorage` ishlatiladi (test/local). Secretlar faqat
environment'dan o'qiladi.
