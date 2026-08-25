"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  apiJson,
  apiPost,
  ConflictError,
  formatPrice,
  ORDER_STATUS_LABELS,
  type OrderDetail,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { ErrorState, Skeleton } from "@/components/States";

export default function OrderDetailPage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = use(params);
  const { status } = useAuth();
  const searchParams = useSearchParams();
  const justCreated = searchParams.get("created") === "1";

  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (status !== "authenticated") return;
    apiJson<OrderDetail>(`/api/v1/customer/orders/${orderId}`)
      .then((data) => {
        setOrder(data);
        setError(null);
      })
      .catch(() => setError("Buyurtma topilmadi"))
      .finally(() => setLoading(false));
  }, [orderId, status]);

  useEffect(() => {
    load();
  }, [load]);

  const cancel = async () => {
    setCancelling(true);
    setCancelError(null);
    try {
      const updated = await apiPost<OrderDetail>(
        `/api/v1/customer/orders/${orderId}/cancel`,
      );
      setOrder(updated);
    } catch (err) {
      setCancelError(
        err instanceof ConflictError
          ? "Bu buyurtmani endi bekor qilib bo'lmaydi"
          : "Bekor qilinmadi",
      );
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <main className="space-y-3 px-4 pt-5">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-40 w-full" />
      </main>
    );
  }

  if (error || !order) return <ErrorState message={error ?? "Topilmadi"} onRetry={load} />;

  return (
    <main className="pb-10">
      <header className="px-4 pb-3 pt-5">
        <Link href="/orders" className="text-xs text-black/40">
          ← Buyurtmalar
        </Link>
        {justCreated && (
          <div className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            Buyurtmangiz qabul qilindi
          </div>
        )}
        <h1 className="mt-3 text-[20px] font-semibold tracking-tight">
          #{order.order_number}
        </h1>
        <p className="mt-1 text-xs text-black/45">
          {order.shop_name} · {ORDER_STATUS_LABELS[order.status] ?? order.status}
        </p>
      </header>

      <ul className="divide-y divide-black/5 border-y border-black/5">
        {order.items.map((item) => (
          <li key={item.id} className="flex justify-between gap-3 px-4 py-3 text-sm">
            <span className="min-w-0">
              <span className="line-clamp-1">{item.product_name}</span>
              <span className="text-xs text-black/40">
                {item.quantity} × {formatPrice(item.unit_price)}
              </span>
            </span>
            <span className="shrink-0 font-medium">{formatPrice(item.line_total)}</span>
          </li>
        ))}
      </ul>

      <div className="flex items-baseline justify-between px-4 py-4">
        <span className="text-sm text-black/50">Jami</span>
        <span className="text-lg font-semibold">{formatPrice(order.total)}</span>
      </div>

      {(order.address_snapshot || order.phone_snapshot || order.comment) && (
        <section className="space-y-1 border-t border-black/5 px-4 py-4 text-xs text-black/55">
          {order.address_snapshot && <p>Manzil: {order.address_snapshot}</p>}
          {order.phone_snapshot && <p>Telefon: {order.phone_snapshot}</p>}
          {order.comment && <p>Izoh: {order.comment}</p>}
        </section>
      )}

      {order.status === "pending" && (
        <div className="px-4 pt-2">
          {cancelError && <p className="mb-2 text-xs text-red-600">{cancelError}</p>}
          <button
            onClick={cancel}
            disabled={cancelling}
            className="w-full rounded-xl border border-black/10 py-2.5 text-sm disabled:opacity-50"
          >
            {cancelling ? "…" : "Buyurtmani bekor qilish"}
          </button>
        </div>
      )}
    </main>
  );
}
