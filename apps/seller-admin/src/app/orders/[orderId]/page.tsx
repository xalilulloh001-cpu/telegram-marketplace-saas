"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  apiFetch,
  formatPrice,
  NEXT_STATUSES,
  ORDER_STATUS_LABELS,
  type SellerOrderDetail,
} from "@/lib/api";
import { useSeller } from "@/components/AuthGuard";

export default function SellerOrderDetail({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = use(params);
  const { permissions } = useSeller();
  const [order, setOrder] = useState<SellerOrderDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canUpdate = permissions.includes("order:update");

  const load = useCallback(
    () =>
      apiFetch(`/api/v1/seller/orders/${orderId}`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data: SellerOrderDetail | null) => setOrder(data)),
    [orderId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const changeStatus = async (status: string) => {
    setBusy(true);
    setError(null);
    const res = await apiFetch(`/api/v1/seller/orders/${orderId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    setBusy(false);
    if (res.ok) {
      setOrder(await res.json());
    } else if (res.status === 409) {
      setError("Bu holatga o'tish mumkin emas");
      await load();
    } else {
      setError("Status o'zgartirilmadi");
    }
  };

  if (!order) return <p className="text-sm text-gray-500">Yuklanmoqda…</p>;

  const nextStatuses = NEXT_STATUSES[order.status] ?? [];

  return (
    <div className="space-y-5">
      <div>
        <Link href="/orders" className="text-xs text-gray-500">
          ← Buyurtmalar
        </Link>
        <h1 className="mt-2 text-xl font-semibold">#{order.order_number}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {ORDER_STATUS_LABELS[order.status] ?? order.status} ·{" "}
          {new Date(order.created_at).toLocaleString("uz-UZ")}
        </p>
      </div>

      <div className="rounded border bg-white">
        <ul className="divide-y">
          {order.items.map((item) => (
            <li key={item.id} className="flex justify-between px-4 py-3 text-sm">
              <span>
                {item.product_name}
                <span className="ml-2 text-xs text-gray-500">
                  {item.quantity} × {formatPrice(item.unit_price)}
                </span>
              </span>
              <span className="font-medium">{formatPrice(item.line_total)}</span>
            </li>
          ))}
        </ul>
        <div className="flex justify-between border-t px-4 py-3 text-sm font-semibold">
          <span>Jami</span>
          <span>{formatPrice(order.total)}</span>
        </div>
      </div>

      <div className="space-y-1 rounded border bg-white p-4 text-sm">
        <p className="text-xs uppercase tracking-wide text-gray-400">Mijoz</p>
        {order.customer_name_snapshot && <p>{order.customer_name_snapshot}</p>}
        {order.phone_snapshot && <p>{order.phone_snapshot}</p>}
        {order.address_snapshot && <p className="text-gray-600">{order.address_snapshot}</p>}
        {order.comment && <p className="text-gray-600">Izoh: {order.comment}</p>}
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {canUpdate && nextStatuses.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {nextStatuses.map((status) => (
            <button
              key={status}
              onClick={() => changeStatus(status)}
              disabled={busy}
              className={`rounded px-4 py-2 text-sm disabled:opacity-50 ${
                status === "cancelled"
                  ? "border border-red-200 text-red-600"
                  : "bg-black text-white"
              }`}
            >
              {ORDER_STATUS_LABELS[status] ?? status}
            </button>
          ))}
        </div>
      )}

      {!canUpdate && (
        <p className="text-sm text-gray-500">Status o&apos;zgartirish huquqingiz yo&apos;q.</p>
      )}
    </div>
  );
}
