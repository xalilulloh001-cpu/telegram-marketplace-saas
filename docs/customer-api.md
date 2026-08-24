# Customer catalog API (Phase 5)

Read-only. Customer sessiyasi (Phase 3 bearer token) talab qilinadi.

```
GET /api/v1/customer/shops
GET /api/v1/customer/shops/{shop_id}
GET /api/v1/customer/shops/{shop_id}/categories
GET /api/v1/customer/shops/{shop_id}/products
GET /api/v1/customer/shops/{shop_id}/products/{product_id}
```

## Ko'rinuvchanlik qoidalari

Filtrlash **query darajasida** bajariladi, response layerida emas — ya'ni yashirin yozuv
umuman o'qilmaydi:

| Obyekt | Ko'rinadi |
|---|---|
| Shop | faqat `status = ACTIVE` |
| Category | faqat `is_active = true` |
| Product | faqat `is_active = true` |

`TRIAL` va `BLOCKED` shoplar customerga ko'rinmaydi. Yashirin obyekt so'ralganda **404** —
mavjud emasdek. Bu Phase 4 dagi cross-tenant policy bilan bir xil.

## Alohida schema'lar

`CustomerShopResponse`, `CustomerCategoryResponse`, `CustomerProductResponse`,
`CustomerProductDetailResponse` — seller schema'laridan **butunlay alohida**. Seller modeliga
yangi maydon qo'shilsa, u customerga tasodifan sizib chiqmaydi.

Customerga **berilmaydi**: `stock` (aniq soni), `status`, `plan_id`, `order_seq`,
`order_prefix`, member ma'lumotlari, internal metadata.

`stock` o'rniga `in_stock: bool` beriladi — mavjudlik ma'lumoti yetarli, aniq qoldiq
raqami esa seller'ning ichki ma'lumoti.

`display_price` — computed field: chegirma bo'lsa `discount_price`, aks holda `price`.
Frontend hisoblamaydi, server aytadi.

## Filter / sort / pagination

```
?search=&category_id=&in_stock=&price_min=&price_max=&sort=&page=&page_size=
```

- `price_min > price_max` → 422; manfiy narx → 422
- `category_id` boshqa shopniki bo'lsa → **404** (bo'sh ro'yxat emas — bu farq muhim:
  bo'sh ro'yxat "kategoriya bor, lekin mahsulot yo'q" degan noto'g'ri signal berardi)
- `sort` — yopiq ro'yxat (`newest`, `price_asc`, `price_desc`, `name_asc`, `name_desc`)
- Pagination Phase 4 standarti: `page_size` 1..100, default 20

## Performance

Mahsulot ro'yxatida rasmlar `selectinload` bilan oldindan yuklanadi — bir sahifa uchun
so'rovlar soni mahsulot soniga bog'liq emas (N+1 yo'q). Product detail'da rasm va
kategoriya birga yuklanadi. Pagination DB darajasida (`LIMIT/OFFSET` + `COUNT`).

Ishlatiladigan indexlar (Phase 4'da yaratilgan, yangi migration kerak bo'lmadi):
`products(shop_id, is_active)`, `products(shop_id, category_id)`, `categories(shop_id)`.

## Realm ajratilishi

Customer tokeni seller/admin endpointlarida 403 oladi va aksincha — testlar bilan qamrab
olingan.

## Rasm URL'lari

Phase 4 storage abstraksiyasi bergan public URL saqlanadi va shundayligicha qaytariladi.
R2 public bucket bilan bu yetarli. Agar kelajakda private bucket kerak bo'lsa, signed URL
generatsiyasi `ObjectStorage` interfeysiga qo'shiladi — customer API kodi o'zgarmaydi.
