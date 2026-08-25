# Checkout & Orders (Phase 7)

> **Checkout is shop-scoped. One checkout creates exactly one order for one shop.**

Xaridorda uchta do'konda savat bo'lsa, u uch marta checkout qiladi. Unified multi-shop
checkout MVP doirasidan ataylab chiqarilgan — schema uni keyinchalik qo'shishga to'sqinlik
qilmaydi (`orders` allaqachon shop-scoped).

## Checkout tranzaksiyasi

Hammasi bitta tranzaksiya ichida:

1. Idempotency key tekshiriladi (mavjud bo'lsa — eski order qaytariladi)
2. Savat topiladi, bo'sh bo'lsa → 409
3. Manzil tekshiriladi (boshqa customerniki → 404)
4. Mahsulotlar **`product_id` o'sish tartibida** `SELECT ... FOR UPDATE` bilan qulflanadi
5. Har biri uchun: faolmi, qoldiq yetarlimi
6. Narx **DB'dan** olinadi (klient yuborgani hech qachon o'qilmaydi)
7. Order + order_items yaratiladi, snapshot bilan
8. Stock kamaytiriladi
9. Savat tozalanadi

Bittasi ham xato bo'lsa — **hammasi rollback**. Qisman order yaratilmaydi.

**Nega lock tartibi muhim?** Ikki checkout bir xil ikkita mahsulotni teskari tartibda
qulflasa, deadlock bo'ladi. `product_id ASC` — barcha tranzaksiyalar uchun bir xil tartib.

## Narx: cart current, order snapshot

| | Cart | Order |
|---|---|---|
| Manba | `products.price` — har o'qishda | `order_items.price_snapshot` — o'zgarmas |
| Sabab | Savat — niyat | Buyurtma — shartnoma |

Savatga qo'shish va checkout orasida seller narxni oshirsa, **checkout yangi narx bilan
hisoblanadi** — server authoritative. Klient yuborgan `subtotal`/`total`/`price` e'tiborsiz
qoldiriladi (schema'da bunday maydonlar umuman yo'q).

`order_items` ikkita narxni saqlaydi: `list_price_snapshot` (chegirmasiz) va
`price_snapshot` (haqiqatda olingan). Shu tufayli chekda chegirma ko'rinadi.

## Snapshot'lar

Order tarixi keyingi o'zgarishlardan himoyalangan:

| Maydon | Nimadan himoya qiladi |
|---|---|
| `product_name_snapshot`, `price_snapshot` | Mahsulot o'chirilishi/narx o'zgarishi (`product_id` → SET NULL, snapshot qoladi) |
| `address_snapshot` | Customer manzilni tahrirlashi |
| `phone_snapshot` | Telefon o'zgarishi |
| `customer_name_snapshot` | Profil o'zgarishi |

## Order number

`orders.id` — global unique PK. `order_number` — shop-scoped: `A-1001`, `B-1001`.

`shops.order_seq` **shop qatorini qulflab** oshiriladi, shuning uchun bir do'konda
parallel checkout'lar bir xil raqam ololmaydi. `UNIQUE(shop_id, order_number)` —
qo'shimcha kafolat.

## Status state machine

```
PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED
   ↓          ↓            ↓
        CANCELLED
```

- `DELIVERED` va `CANCELLED` — terminal holatlar
- Bosqichni tashlab o'tib bo'lmaydi (`PENDING → DELIVERED` → 409)
- Noma'lum status → 422 (enum darajasida)

**Stock qaytarilishi:** buyurtma `PENDING`/`CONFIRMED`/`PROCESSING`/`SHIPPED` holatidan
bekor qilinsa, qoldiq javonga qaytariladi (tranzaksiya ichida).

**Customer bekor qilishi:** faqat `PENDING` holatida. Seller tasdiqlagach — bu sellerning
qarori.

## Idempotency

Telegram Mini App'da tasdiqlash tugmasi ikki marta bosilishi mumkin. Yechim:
klient checkout ekraniga kirganda bitta `idempotency_key` generatsiya qiladi va uni
so'rov bilan yuboradi.

- Server avval shu kalit bo'yicha order qidiradi — topsa, **o'shani qaytaradi**
- `UNIQUE(customer_id, idempotency_key)` — poyga holatida ham ikkinchi order yaratilmaydi
  (`IntegrityError` tutiladi va mavjud order qaytariladi)

Kalit ixtiyoriy: usiz ham checkout ishlaydi, lekin himoya bo'lmaydi.

## Mavjud bo'lmagan mahsulot

Checkout paytida mahsulot nofaol bo'lsa yoki qoldiq yetmasa: **409** va javobda qaysi
qator muammoli ekani aniq ko'rsatiladi:

```json
{"detail": {"message": "some items are no longer available",
  "items": [{"product_id": 7, "product_name": "...", "reason": "insufficient_stock",
             "available_stock": 3}]}}
```

Savat **tozalanmaydi** — xaridor nima qilishni o'zi hal qiladi.

## API

```
POST   /api/v1/customer/shops/{shop_id}/checkout
GET    /api/v1/customer/orders
GET    /api/v1/customer/orders/{order_id}
POST   /api/v1/customer/orders/{order_id}/cancel

GET    /api/v1/seller/orders?status=          ORDER_VIEW
GET    /api/v1/seller/orders/{order_id}       ORDER_VIEW
PATCH  /api/v1/seller/orders/{order_id}/status  ORDER_UPDATE
```

## Tenant izolyatsiyasi

Customer faqat o'z orderlarini (`customer_id` sessiyadan), seller faqat o'z do'koni
orderlarini (`shop_id` sessiyadan) ko'radi. Boshqasi → **404**.

## Performance

Order list va detail'da `items` va `shop` `selectinload` bilan yuklanadi — N+1 yo'q.
Pagination DB darajasida. Yangi indexlar: `(customer_id, created_at)` — "mening
buyurtmalarim, yangisidan", `(shop_id, status, created_at)` — seller board filtri.
