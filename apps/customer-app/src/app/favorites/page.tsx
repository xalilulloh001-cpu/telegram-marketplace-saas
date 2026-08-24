"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiJson, apiSend, formatPrice, type Favorite, type Page } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { EmptyState, ErrorState, Skeleton } from "@/components/States";

export default function FavoritesPage() {
  const { status } = useAuth();
  const [favorites, setFavorites] = useState<Page<Favorite> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (status !== "authenticated") return;
    apiJson<Page<Favorite>>("/api/v1/customer/favorites?page_size=50")
      .then((data) => {
        setFavorites(data);
        setError(null);
      })
      .catch(() => setError("Sevimlilarni yuklab bo'lmadi"))
      .finally(() => setLoading(false));
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  const remove = async (productId: number) => {
    try {
      await apiSend(`/api/v1/customer/favorites/${productId}`, "DELETE");
      load();
    } catch {
      load();
    }
  };

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

  const items = favorites?.items ?? [];

  return (
    <main className="pb-10">
      <header className="px-4 pb-3 pt-5">
        <Link href="/" className="text-xs text-black/40">
          ← Do&apos;konlar
        </Link>
        <h1 className="mt-2 text-[20px] font-semibold tracking-tight">Sevimlilar</h1>
      </header>

      {items.length === 0 ? (
        <EmptyState title="Sevimlilar bo'sh" hint="Mahsulotdagi ♡ tugmasini bosing" />
      ) : (
        <ul className="divide-y divide-black/5">
          {items.map((favorite) => (
            <li key={favorite.product_id} className="flex items-center gap-3 px-4 py-3">
              <Link
                href={`/shop/${favorite.shop_id}/product/${favorite.product_id}`}
                className="flex min-w-0 flex-1 items-center gap-3"
              >
                <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-black/[0.03]">
                  {favorite.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={favorite.image_url}
                      alt={favorite.product_name}
                      className="h-full w-full object-cover"
                    />
                  ) : null}
                </div>
                <div className="min-w-0">
                  <p className="line-clamp-2 text-[13px] leading-snug">
                    {favorite.product_name}
                  </p>
                  <p className="mt-1 text-sm font-semibold">
                    {formatPrice(favorite.display_price)}
                  </p>
                  {!favorite.is_available && (
                    <p className="text-[11px] text-black/40">Hozircha mavjud emas</p>
                  )}
                </div>
              </Link>
              <button
                onClick={() => remove(favorite.product_id)}
                className="shrink-0 text-lg text-red-500"
                aria-label="Sevimlilardan olib tashlash"
              >
                ♥
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
