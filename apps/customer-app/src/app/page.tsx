"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiJson, type Page, type Shop } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { EmptyState, ErrorState, Skeleton } from "@/components/States";

export default function Discovery() {
  const { status } = useAuth();
  const [shops, setShops] = useState<Page<Shop> | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (status !== "authenticated") return;
    const params = new URLSearchParams({ page_size: "50", sort: "name_asc" });
    if (search) params.set("search", search);
    apiJson<Page<Shop>>(`/api/v1/customer/shops?${params}`)
      .then((data) => {
        setShops(data);
        setError(null);
      })
      .catch(() => setError("Do'konlarni yuklab bo'lmadi"))
      .finally(() => setLoading(false));
  }, [search, status]);

  // Every state update lands in a promise callback, never synchronously in the effect.
  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="px-4 pb-10 pt-5">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-semibold tracking-tight">Do&apos;konlar</h1>
        <Link href="/favorites" className="text-xs text-black/50">
          Sevimlilar
        </Link>
      </div>

      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Do'kon qidirish"
        className="mt-3 w-full rounded-xl bg-black/[0.04] px-4 py-2.5 text-sm outline-none placeholder:text-black/30"
      />

      <div className="mt-4 space-y-2">
        {loading &&
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[68px] w-full" />)}

        {!loading && error && <ErrorState message={error} onRetry={load} />}

        {!loading && !error && shops?.items.length === 0 && (
          <EmptyState title="Do'kon topilmadi" hint="Boshqa nom bilan qidirib ko'ring" />
        )}

        {!loading &&
          !error &&
          shops?.items.map((shop) => (
            <Link
              key={shop.id}
              href={`/shop/${shop.id}`}
              className="flex items-center gap-3 rounded-2xl border border-black/5 p-3 active:bg-black/[0.02]"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-black/[0.04] text-sm font-semibold">
                {shop.logo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={shop.logo_url} alt={shop.name} className="h-full w-full object-cover" />
                ) : (
                  shop.name.slice(0, 1)
                )}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{shop.name}</p>
                {shop.description && (
                  <p className="truncate text-xs text-black/40">{shop.description}</p>
                )}
              </div>
            </Link>
          ))}
      </div>
    </main>
  );
}
