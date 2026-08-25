"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  apiJson,
  apiPost,
  ConflictError,
  formatPrice,
  type Cart,
  type CheckoutConflict,
  type OrderDetail,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { EmptyState, ErrorState, Skeleton } from "@/components/States";

export default function CheckoutPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { shopId } = use(params);
  const { status } = useAuth();
  const router = useRouter();

  const [cart, setCart] = useState<Cart | null>(null);
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<CheckoutConflict | null>(null);
  const [loading, setLoading] = useState(true);

  // One key per visit to this screen: tapping confirm twice replays the same key, so the
  // server returns the order it already created instead of making a second one.
  // Generated lazily on first use — randomness during render is not allowed.
  const idempotencyKeyRef = useRef<string | null>(null);
  const getIdempotencyKey = () => {
    if (idempotencyKeyRef.current === null) {
      idempotencyKeyRef.current = `${shopId}-${Date.now()}-${crypto.randomUUID()}`;
    }
    return idempotencyKeyRef.current;
  };

  const load = useCallback(() => {
    if (status !== "authenticated") return;
    apiJson<Cart>(`/api/v1/customer/shops/${shopId}/cart`)
      .then((data) => {
        setCart(data);
        setError(null);
      })
      .catch(() => setError("Savatni yuklab bo'lmadi"))
      .finally(() => setLoading(false));
  }, [shopId, status]);

  useEffect(() => {
    load();
  }, [load]);

  const confirm = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    setConflict(null);
    try {
      const order = await apiPost<OrderDetail>(
        `/api/v1/customer/shops/${shopId}/checkout`,
        {
          phone: phone || null,
          comment: comment || null,
          idempotency_key: getIdempotencyKey(),
        },
      );
      router.replace(`/orders/${order.id}?created=1`);
    } catch (err) {
      if (err instanceof ConflictError && typeof err.detail !== "string") {
        setConflict(err.detail);
      } else if (err instanceof ConflictError) {
        setError(err.message === "cart is empty" ? "Savat bo'sh" : err.message);
      } else {
        setError("Buyurtma yaratilmadi. Qayta urinib ko'ring.");
      }
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="space-y-3 px-4 pt-5">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-32 w-full" />
      </main>
    );
  }

  if (error && !cart) return <ErrorState message={error} onRetry={load} />;

  const items = cart?.items.filter((i) => i.available) ?? [];
  if (items.length === 0) {
    return (
      <main className="px-4 pt-5">
        <Link href={`/shop/${shopId}/cart`} className="text-xs text-black/40">
          ← Savatga qaytish
        </Link>
        <EmptyState title="Savat bo'sh" hint="Buyurtma berish uchun mahsulot qo'shing" />
      </main>
    );
  }

  return (
    <main className="pb-36">
      <header className="px-4 pb-3 pt-5">
        <Link href={`/shop/${shopId}/cart`} className="text-xs text-black/40">
          ← Savatga qaytish
        </Link>
        <h1 className="mt-2 text-[20px] font-semibold tracking-tight">Buyurtmani rasmiylashtirish</h1>
      </header>

      <section className="px-4">
        <ul className="divide-y divide-black/5 rounded-2xl border border-black/5">
          {items.map((item) => (
            <li key={item.item_id} className="flex justify-between gap-3 px-3 py-2.5 text-sm">
              <span className="min-w-0">
                <span className="line-clamp-1">{item.product_name}</span>
                <span className="text-xs text-black/40">
                  {item.quantity} × {formatPrice(item.display_price)}
                </span>
              </span>
              <span className="shrink-0 font-medium">{formatPrice(item.line_total)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3 px-4 pt-5">
        <label className="block text-sm">
          <span className="text-xs text-black/50">Yetkazib berish manzili</span>
          <textarea
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            rows={2}
            placeholder="Shahar, ko'cha, uy"
            className="mt-1 w-full rounded-xl bg-black/[0.04] px-3 py-2 text-sm outline-none"
          />
        </label>
        <label className="block text-sm">
          <span className="text-xs text-black/50">Telefon</span>
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            inputMode="tel"
            placeholder="+998 90 123 45 67"
            className="mt-1 w-full rounded-xl bg-black/[0.04] px-3 py-2 text-sm outline-none"
          />
        </label>
        <label className="block text-sm">
          <span className="text-xs text-black/50">Izoh</span>
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Ixtiyoriy"
            className="mt-1 w-full rounded-xl bg-black/[0.04] px-3 py-2 text-sm outline-none"
          />
        </label>
      </section>

      {conflict && (
        <div className="mx-4 mt-4 rounded-xl bg-red-50 p-3 text-xs text-red-700">
          <p className="font-medium">Buyurtma berilmadi</p>
          <ul className="mt-1 space-y-0.5">
            {conflict.items.map((item) => (
              <li key={item.product_id}>
                {item.product_name} —{" "}
                {item.reason === "insufficient_stock"
                  ? `qoldiq o'zgargan (${item.available_stock} ta qoldi)`
                  : "hozircha mavjud emas"}
              </li>
            ))}
          </ul>
          <Link href={`/shop/${shopId}/cart`} className="mt-2 inline-block underline">
            Savatni yangilash
          </Link>
        </div>
      )}

      {error && <p className="px-4 pt-3 text-center text-xs text-red-600">{error}</p>}

      <div className="fixed inset-x-0 bottom-0 mx-auto max-w-lg border-t border-black/5 bg-white/95 p-4 backdrop-blur">
        <div className="mb-3 flex items-baseline justify-between">
          <span className="text-xs text-black/50">{cart?.total_items} ta mahsulot</span>
          <span className="text-lg font-semibold">{formatPrice(cart?.subtotal ?? "0")}</span>
        </div>
        <button
          onClick={confirm}
          disabled={submitting}
          className="w-full rounded-xl bg-black py-3 text-sm font-medium text-white disabled:bg-black/20"
        >
          {submitting ? "Yuborilmoqda…" : "Buyurtmani tasdiqlash"}
        </button>
      </div>
    </main>
  );
}
