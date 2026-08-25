"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiJson, formatPrice, ORDER_STATUS_LABELS, type Order, type Page } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { EmptyState, ErrorState, Skeleton } from "@/components/States";

export default function OrdersPage() {
  const { status } = useAuth();
  const [orders, setOrders] = useState<Page<Order> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (status !== "authenticated") return;
    apiJson<Page<Order>>("/api/v1/customer/orders?page_size=50")
      .then((data) => {
        setOrders(data);
        setError(null);
      })
      .catch(() => setError("Buyurtmalarni yuklab bo'lmadi"))
      .finally(() => setLoading(false));
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <main className="space-y-3 px-4 pt-5">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </main>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const items = orders?.items ?? [];

  return (
    <main className="pb-10">
      <header className="px-4 pb-3 pt-5">
        <Link href="/" className="text-xs text-black/40">
          ← Do&apos;konlar
        </Link>
        <h1 className="mt-2 text-[20px] font-semibold tracking-tight">Buyurtmalarim</h1>
      </header>

      {items.length === 0 ? (
        <EmptyState title="Buyurtma yo'q" hint="Birinchi buyurtmangizni bering" />
      ) : (
        <ul className="divide-y divide-black/5">
          {items.map((order) => (
            <li key={order.id}>
              <Link href={`/orders/${order.id}`} className="block px-4 py-3">
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-medium">#{order.order_number}</span>
                  <span className="text-sm font-semibold">{formatPrice(order.total)}</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-black/45">
                  <span>{order.shop_name}</span>
                  <span>{ORDER_STATUS_LABELS[order.status] ?? order.status}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
