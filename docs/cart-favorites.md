# Cart & Favorites (Phase 6)

## Asosiy farq: cart shop-scoped, favorites global

```
Customer (global)
 ├── Cart → Shop A     (alohida)
 ├── Cart → Shop B     (alohida)
 └── Favorites          (barcha shoplar bo'ylab bitta ro'yxat)
```

Savat har do'kon uchun alohida — Shop A mahsuloti Shop B savatiga tushmaydi
(`UNIQUE(customer_id, shop_id)`). Sevimlilar esa customerga tegishli va bir nechta
do'kon mahsulotlarini o'z ichiga oladi (`UNIQUE(customer_id, product_id)`).

## Endpointlar

```
GET    /api/v1/customer/shops/{shop_id}/cart
POST   /api/v1/customer/shops/{shop_id}/cart/items
PATCH  /api/v1/customer/shops/{shop_id}/cart/items/{item_id}
DELETE /api/v1/customer/shops/{shop_id}/cart/items/{item_id}
DELETE /api/v1/customer/shops/{shop_id}/cart

GET    /api/v1/customer/favorites
PUT    /api/v1/customer/favorites/{product_id}
DELETE /api/v1/customer/favorites/{product_id}
```

Har bir mutatsiya **qayta hisoblangan to'liq savatni** qaytaradi — frontend jamini
o'zi hisoblamaydi, serverdan kelganini qabul qiladi.

**Nega favorites'da PUT, POST emas?** Sevimliga qo'shish idempotent amal: ikki marta
bosilsa ham natija bir xil. PUT aynan shuni bildiradi va takroriy so'rov xato bermaydi.
Toggle endpoint qilinmadi — u idempotent emas va tarmoq qайta urinishida holatni
teskari aylantirib yuborishi mumkin edi.

## Narx: cart current, order snapshot

Bu ikki tushuncha ataylab farqlanadi:

| | Cart (Phase 6) | Order (Phase 7) |
|---|---|---|
| Narx manbai | `products.price` — har o'qishda qayta hisoblanadi | `order_items.price_snapshot` — o'zgarmas |
| Sabab | Savat — bu niyat. Seller narxni o'zgartirsa, xaridor yangi narxni ko'rishi kerak | Buyurtma — bu shartnoma. Keyin narx o'zgarsa ham tarix buzilmaydi |

Chegirma bo'lsa `display_price = discount_price`, aks holda `price`. Jami serverda
`Decimal` bilan hisoblanadi, float ishlatilmaydi. Frontend yuborgan `subtotal` **hech
qachon o'qilmaydi**.

## Mavjud bo'lmagan mahsulot

Seller mahsulotni nofaol qilsa yoki qoldiq tugasa, savat qatori **o'chirilmaydi** —
`available: false` bayrog'i bilan qoladi.

Sabab: qator jimgina yo'qolsa, xaridor jami nega o'zgarganini tushunmaydi. Bayroq bilan
esa aniq ko'radi. Bunday qator jamiga **qo'shilmaydi** (`subtotal` va `total_items`dan
chiqarib tashlanadi), shuning uchun noto'g'ri summa ko'rsatilmaydi. Checkout (Phase 7)
shu bayroqqa qarab bloklaydi.

Sevimlilarda ham xuddi shunday: `is_available: false`. Lekin discovery API'da nofaol
mahsulot umuman ko'rinmaydi — sevimlilar shaxsiy ro'yxat, katalog esa vitrina.

## Stock validatsiyasi va concurrency

Savatga qo'shishda mahsulot qatori `SELECT ... FOR UPDATE` bilan **qulflanadi**, keyin
qoldiq tekshiriladi. Shu tufayli bir vaqtda kelgan ikki so'rov bir xil qoldiqni ikki
marta "band qila" olmaydi:

```
stock = 5
request A: quantity 4  → 201
request B: quantity 4  → 409 (qulf ochilgach 4+4 > 5)
```

Mavjud qator ustiga qo'shilganda ham jami tekshiriladi (2 + 4 > 5 → 409), ya'ni
bosqichma-bosqich limitdan oshirib bo'lmaydi. `UNIQUE(cart_id, product_id)` — oxirgi
himoya qatlami: `IntegrityError` tutiladi va 409 qaytariladi.

Barcha amallar bitta tranzaksiya ichida; xato bo'lsa rollback.

## Savatni tozalash

`DELETE /cart` — qatorlar o'chadi, **savat qatorining o'zi qoladi**. Shunda checkout
har doim mavjud savatga ulanadi va "savat yo'q" holatini alohida qayrab o'tirish
kerak bo'lmaydi.

## Tenant izolyatsiyasi

Savat **hech qachon** klient bergan `cart_id` orqali topilmaydi — faqat
`(customer_id, shop_id)` juftligi bilan, ikkalasi ham serverdan: `customer_id`
sessiyadan, `shop_id` URL'dan lekin do'kon mavjudligi tekshirilgach. Savat qatorlari
esa faqat o'z savati orqali topiladi.

Natijada quyidagilar **404** oladi (403 emas — ID mavjudligini oshkor qilmaslik uchun):
boshqa customer'ning qatori, boshqa do'kon mahsuloti, boshqa do'kon endpointidagi qator.

Realm ajratilishi: seller/admin tokeni customer endpointlarida 403.

## Performance

Savat o'qishda `Cart → items → product → images` zanjiri `selectinload` bilan bir
so'rovda yuklanadi — qatorlar soni qancha bo'lishidan qat'i nazar so'rovlar soni
o'zgarmaydi (N+1 yo'q). Sevimlilarda ham shunday. Pagination DB darajasida.

## Migration

**Yaratilmadi.** Phase 2 schema'si yetarli: `carts`, `cart_items`, `favorites`
jadvallari, kerakli unique constraint'lar (`uq_carts_customer_shop`,
`uq_cart_items_cart_product`, `uq_favorites_customer_product`) va `CHECK (qty > 0)`
allaqachon mavjud. Unique constraint'lar o'z indexlarini yaratadi va so'rov naqshlarimizni
qamrab oladi, shuning uchun yangi index ham qo'shilmadi.
