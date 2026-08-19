# Database schema (Phase 2)

16 ta jadval. Tenant kaliti — `shop_id`.

## Global (shop_id YO'Q)
`users`, `customers`, `addresses`, `plans`, `platform_admins`

Customer global: bitta Telegram user bir nechta shopda xarid qila oladi.

## Shop-scoped (shop_id BOR)
`shop_members`, `categories`, `products`, `product_images`, `carts`, `favorites`, `orders`, `subscriptions`

## Muhim qarorlar

**Order raqamlash.** `orders.id` — global unique PK. `orders.order_number` — shop-scoped
(`uq_orders_shop_order_number` = shop_id + order_number). `shops.order_prefix` va `shops.order_seq`
har shopga o'z ketma-ketligini beradi: Shop A → `#A-1001`, Shop B → `#B-1001`.

**Snapshot.** `order_items.price_snapshot` va `product_name_snapshot` — NOT NULL. Buyurtma
yaratilgandan keyin mahsulot narxi o'zgarsa yoki o'chirilsa ham, order tarixi o'zgarmaydi.
`orders.address_snapshot`/`phone_snapshot` ham shu maqsadda.

**Frontend qiymatlariga ishonmaslik.** `total_amount`, `price_snapshot`, `qty`, `stock` uchun
CHECK constraint'lar (manfiy bo'lmaslik, qty > 0, discount_price <= price). Bular oxirgi himoya
qatlami — asosiy tekshiruv Phase 7'da service layer'da bo'ladi (narx DB'dan olinadi).

**Cascade siyosati.** Shop o'chirilsa uning katalogi/savatlari ham o'chadi (CASCADE), lekin
`orders` — RESTRICT (moliyaviy tarix saqlanadi). `order_items.product_id` — SET NULL
(mahsulot o'chsa ham order buzilmaydi, snapshot qoladi).

**Variantlar (o'lcham/rang).** MVP'da yo'q. Kelajakda `product_variants` jadvali qo'shilib,
`cart_items`/`order_items`ga nullable `variant_id` qo'shiladi — mavjud schema buzilmaydi.

## RLS holati

**Hozircha yoqilmagan** — arxitekturada tasdiqlanganidek, RLS Phase 11 (production hardening)da
qo'shiladi. Schema unga tayyor: har bir tenant jadvalida `shop_id` mavjud, shuning uchun policy
qo'shish uchun migration'dan boshqa hech narsa o'zgarmaydi:

```sql
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON products
  USING (shop_id = current_setting('app.current_shop_id')::int);
```

Hozirgi himoya — ilova darajasida (Phase 4'da repository layer'da `shop_id` majburiy parametr).
