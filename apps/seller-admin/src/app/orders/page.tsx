"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  apiFetch,
  formatPrice,
  ORDER_STATUS_LABELS,
  type Order,
  type Page,
} from "@/lib/api";

const FILTERS = [
  ["", "Hammasi"],
  ["pending", "Kutilmoqda"],
  ["confirmed", "Tasdiqlangan"],
  ["processing", "Tayyorlanmoqda"],
  ["shipped", "Yo'lda"],
  ["delivered", "Yetkazilgan"],
] as const;

export default function OrdersPage() {
  const [page, setPage] = useState<Page<Order> | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [pageNum, setPageNum] = useState(1);

  const load = useCallback(() => {
    const params = new URLSearchParams({ page: String(pageNum), page_size: "20" });
    if (statusFilter) params.set("status", statusFilter);
    return apiFetch(`/api/v1/seller/orders?${params}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: Page<Order> | null) => setPage(data));
  }, [pageNum, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Buyurtmalar</h1>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map(([value, label]) => (
          <button
            key={value || "all"}
            onClick={() => {
              setStatusFilter(value);
              setPageNum(1);
            }}
            className={`rounded-full px-3 py-1.5 text-xs ${
              statusFilter === value ? "bg-black text-white" : "bg-black/[0.06]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <ul className="divide-y rounded border bg-white">
        {page?.items.map((order) => (
          <li key={order.id}>
            <Link
              href={`/orders/${order.id}`}
              className="flex items-center justify-between px-4 py-3 text-sm hover:bg-black/[0.02]"
            >
              <span>
                <span className="font-medium">#{order.order_number}</span>
                <span className="ml-3 text-xs text-gray-500">
                  {new Date(order.created_at).toLocaleDateString("uz-UZ")}
                </span>
              </span>
              <span className="flex items-center gap-4">
                <span className="text-xs text-gray-500">
                  {ORDER_STATUS_LABELS[order.status] ?? order.status}
                </span>
                <span className="font-medium">{formatPrice(order.total)}</span>
              </span>
            </Link>
          </li>
        ))}
        {page?.items.length === 0 && (
          <li className="px-4 py-3 text-sm text-gray-500">Buyurtma yo&apos;q</li>
        )}
      </ul>

      {page && page.pages > 1 && (
        <div className="flex items-center gap-3 text-sm">
          <button
            disabled={pageNum <= 1}
            onClick={() => setPageNum((n) => n - 1)}
            className="rounded border px-3 py-1 disabled:opacity-40"
          >
            Oldingi
          </button>
          <span>
            {page.page} / {page.pages} ({page.total} ta)
          </span>
          <button
            disabled={pageNum >= page.pages}
            onClick={() => setPageNum((n) => n + 1)}
            className="rounded border px-3 py-1 disabled:opacity-40"
          >
            Keyingi
          </button>
        </div>
      )}
    </div>
  );
}
