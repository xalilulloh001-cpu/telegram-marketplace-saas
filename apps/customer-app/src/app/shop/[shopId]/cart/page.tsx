"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiJson, apiSend, formatPrice, type Cart } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { EmptyState, ErrorState, Skeleton } from "@/components/States";

export default function CartPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { shopId } = use(params);
  const { status } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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

  // The server returns the recomputed cart from every mutation, so the UI never has to
  // guess at totals — it just adopts what came back.
  const mutate = async (itemId: number, fn: () => Promise<Cart | undefined>) => {
    setPendingId(itemId);
    setNotice(null);
    try {
      const updated = await fn();
      if (updated) setCart(updated);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Amal bajarilmadi");
      load();
    } finally {
      setPendingId(null);
    }
  };

  const setQuantity = (itemId: number, quantity: number) =>
    mutate(itemId, () =>
      apiSend<Cart>(`/api/v1/customer/shops/${shopId}/cart/items/${itemId}`, "PATCH", {
        quantity,
      }),
    );

  const removeItem = (itemId: number) =>
    mutate(itemId, () =>
      apiSend<Cart>(`/api/v1/customer/shops/${shopId}/cart/items/${itemId}`, "DELETE"),
    );

  if (loading) {
    return (
      <main className="space-y-3 px-4 pt-5">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </main>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const items = cart?.items ?? [];

  return (
    <main className="pb-32">
      <header className="px-4 pb-3 pt-5">
        <Link href={`/shop/${shopId}`} className="text-xs text-black/40">
          ← Do&apos;konga qaytish
        </Link>
        <h1 className="mt-2 text-[20px] font-semibold tracking-tight">Savat</h1>
      </header>

      {notice && <p className="px-4 pb-2 text-xs text-red-600">{notice}</p>}

      {items.length === 0 ? (
        <EmptyState title="Savat bo'sh" hint="Mahsulot qo'shib, keyin bu yerga qayting" />
      ) : (
        <ul className="divide-y divide-black/5">
          {items.map((item) => (
            <li
              key={item.item_id}
              className={`flex gap-3 px-4 py-3 ${pendingId === item.item_id ? "opacity-50" : ""}`}
            >
              <div className="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-black/[0.03]">
                {item.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.image_url}
                    alt={item.product_name}
                    className="h-full w-full object-cover"
                  />
                ) : null}
              </div>

              <div className="min-w-0 flex-1">
                <p className="line-clamp-2 text-[13px] leading-snug">{item.product_name}</p>
                {!item.available && (
                  <p className="mt-0.5 text-[11px] text-red-500">Hozircha mavjud emas</p>
                )}
                <p className="mt-1 text-sm font-semibold">{formatPrice(item.line_total)}</p>

                <div className="mt-2 flex items-center gap-3">
                  <div className="flex items-center rounded-full bg-black/[0.05]">
                    <button
                      onClick={() => setQuantity(item.item_id, item.quantity - 1)}
                      disabled={item.quantity <= 1 || pendingId !== null}
                      className="h-7 w-8 text-sm disabled:opacity-30"
                    >
                      −
                    </button>
                    <span className="min-w-6 text-center text-xs">{item.quantity}</span>
                    <button
                      onClick={() => setQuantity(item.item_id, item.quantity + 1)}
                      disabled={pendingId !== null}
                      className="h-7 w-8 text-sm disabled:opacity-30"
                    >
                      +
                    </button>
                  </div>
                  <button
                    onClick={() => removeItem(item.item_id)}
                    disabled={pendingId !== null}
                    className="text-[11px] text-black/40"
                  >
                    O&apos;chirish
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {items.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 mx-auto max-w-lg border-t border-black/5 bg-white/95 p-4 backdrop-blur">
          <div className="mb-3 flex items-baseline justify-between">
            <span className="text-xs text-black/50">{cart?.total_items} ta mahsulot</span>
            <span className="text-lg font-semibold">{formatPrice(cart?.subtotal ?? "0")}</span>
          </div>
          <button
            disabled
            className="w-full cursor-not-allowed rounded-xl bg-black/10 py-3 text-sm font-medium text-black/40"
          >
            Checkout — tez orada
          </button>
        </div>
      )}
    </main>
  );
}
