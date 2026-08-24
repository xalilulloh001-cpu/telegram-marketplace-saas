"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiJson, apiSend, formatPrice, NotFoundError, type Cart, type ProductDetail } from "@/lib/api";
import { FavoriteButton } from "@/components/FavoriteButton";
import { useAuth } from "@/components/AuthProvider";
import { ErrorState, Skeleton } from "@/components/States";

export default function ProductPage({
  params,
}: {
  params: Promise<{ shopId: string; productId: string }>;
}) {
  const { shopId, productId } = use(params);
  const { status } = useAuth();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [activeImage, setActiveImage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (status !== "authenticated") return;
    apiJson<ProductDetail>(`/api/v1/customer/shops/${shopId}/products/${productId}`)
      .then((data) => {
        setProduct(data);
        setError(null);
      })
      .catch((err: Error) =>
        setError(err instanceof NotFoundError ? "Mahsulot topilmadi" : "Xatolik yuz berdi"),
      )
      .finally(() => setLoading(false));
  }, [productId, shopId, status]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <main className="px-4 pt-5">
        <Skeleton className="aspect-square w-full rounded-2xl" />
        <Skeleton className="mt-4 h-5 w-2/3" />
        <Skeleton className="mt-2 h-6 w-1/3" />
      </main>
    );
  }

  if (error || !product) {
    return <ErrorState message={error ?? "Mahsulot topilmadi"} onRetry={load} />;
  }

  const addToCart = async () => {
    setAdding(true);
    setAddError(null);
    try {
      await apiSend<Cart>(`/api/v1/customer/shops/${shopId}/cart/items`, "POST", {
        product_id: product.id,
        quantity: 1,
      });
      setAdded(true);
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Savatga qo'shilmadi");
    } finally {
      setAdding(false);
    }
  };

  const discounted = product.discount_price !== null;
  const images = product.images.length > 0 ? product.images : null;

  return (
    <main className="pb-28">
      <div className="px-4 pt-5">
        <div className="flex items-center justify-between">
          <Link href={`/shop/${shopId}`} className="text-xs text-black/40">
            ← Do&apos;konga qaytish
          </Link>
          <FavoriteButton productId={product.id} size="lg" />
        </div>
      </div>

      <div className="mt-3 px-4">
        <div className="aspect-square overflow-hidden rounded-2xl bg-black/[0.03]">
          {images ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={images[activeImage].url}
              alt={product.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-black/25">
              Rasm yo&apos;q
            </div>
          )}
        </div>

        {images && images.length > 1 && (
          <div className="mt-3 flex gap-2 overflow-x-auto">
            {images.map((image, index) => (
              <button
                key={image.id}
                onClick={() => setActiveImage(index)}
                className={`h-14 w-14 shrink-0 overflow-hidden rounded-lg border-2 ${
                  index === activeImage ? "border-black" : "border-transparent"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={image.url} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>

      <section className="px-4 pt-5">
        {product.category && (
          <p className="text-[11px] uppercase tracking-wide text-black/35">
            {product.category.name}
          </p>
        )}
        <h1 className="mt-1 text-[19px] font-semibold leading-snug tracking-tight">
          {product.name}
        </h1>

        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl font-semibold">{formatPrice(product.display_price)}</span>
          {discounted && (
            <span className="text-sm text-black/35 line-through">
              {formatPrice(product.price)}
            </span>
          )}
        </div>

        <p className={`mt-2 text-xs ${product.in_stock ? "text-emerald-600" : "text-black/40"}`}>
          {product.in_stock ? "Mavjud" : "Hozircha mavjud emas"}
        </p>

        {product.description && (
          <p className="mt-5 whitespace-pre-line text-sm leading-relaxed text-black/70">
            {product.description}
          </p>
        )}
      </section>

      <div className="fixed inset-x-0 bottom-0 mx-auto max-w-lg border-t border-black/5 bg-white/95 p-4 backdrop-blur">
        {addError && <p className="mb-2 text-center text-xs text-red-600">{addError}</p>}
        {added ? (
          <Link
            href={`/shop/${shopId}/cart`}
            className="block w-full rounded-xl bg-black py-3 text-center text-sm font-medium text-white"
          >
            Savatga qo&apos;shildi — savatni ochish
          </Link>
        ) : (
          <button
            onClick={addToCart}
            disabled={!product.in_stock || adding}
            className="w-full rounded-xl bg-black py-3 text-sm font-medium text-white disabled:bg-black/10 disabled:text-black/40"
          >
            {!product.in_stock ? "Mavjud emas" : adding ? "Qo'shilmoqda…" : "Savatga qo'shish"}
          </button>
        )}
      </div>
    </main>
  );
}
