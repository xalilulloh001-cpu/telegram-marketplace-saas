"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  apiJson,
  NotFoundError,
  type Category,
  type Page,
  type Product,
  type ShopDetail,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { ProductCard } from "@/components/ProductCard";
import { EmptyState, ErrorState, ProductGridSkeleton, Skeleton } from "@/components/States";

const SORTS = [
  ["newest", "Yangi"],
  ["price_asc", "Arzon"],
  ["price_desc", "Qimmat"],
  ["name_asc", "A-Z"],
] as const;

export default function ShopPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { shopId } = use(params);
  const id = Number(shopId);
  const { status } = useAuth();

  const [shop, setShop] = useState<ShopDetail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Page<Product> | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<string>("newest");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    apiJson<ShopDetail>(`/api/v1/customer/shops/${id}`)
      .then(setShop)
      .catch((err: Error) =>
        setError(err instanceof NotFoundError ? "Do'kon topilmadi" : "Xatolik yuz berdi"),
      );
    apiJson<Category[]>(`/api/v1/customer/shops/${id}/categories`)
      .then(setCategories)
      .catch(() => setCategories([]));
  }, [id, status]);

  const loadProducts = useCallback(() => {
    if (status !== "authenticated") return;
    const params = new URLSearchParams({ page_size: "24", sort });
    if (categoryId) params.set("category_id", String(categoryId));
    if (search) params.set("search", search);
    apiJson<Page<Product>>(`/api/v1/customer/shops/${id}/products?${params}`)
      .then((data) => {
        setProducts(data);
        setError(null);
      })
      .catch(() => setError("Mahsulotlarni yuklab bo'lmadi"))
      .finally(() => setLoading(false));
  }, [categoryId, id, search, sort, status]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  const roots = categories.filter((c) => c.parent_id === null);
  const childrenOf = (parentId: number) => categories.filter((c) => c.parent_id === parentId);

  return (
    <main className="pb-12">
      <header className="border-b border-black/5 px-4 pb-4 pt-5">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-xs text-black/40">
            ← Do&apos;konlar
          </Link>
          <div className="flex gap-3 text-xs">
            <Link href="/favorites" className="text-black/50">
              Sevimlilar
            </Link>
            <Link href={`/shop/${id}/cart`} className="font-medium">
              Savat
            </Link>
          </div>
        </div>
        {shop ? (
          <>
            <h1 className="mt-2 text-[20px] font-semibold tracking-tight">{shop.name}</h1>
            {shop.description && <p className="mt-1 text-sm text-black/50">{shop.description}</p>}
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-black/40">
              {shop.contact_phone && <span>{shop.contact_phone}</span>}
              {shop.city && <span>{shop.city}</span>}
            </div>
          </>
        ) : (
          <Skeleton className="mt-2 h-6 w-40" />
        )}
      </header>

      {categories.length > 0 && (
        <nav className="flex gap-2 overflow-x-auto border-b border-black/5 px-4 py-3 text-xs">
          <button
            onClick={() => setCategoryId(null)}
            className={`shrink-0 rounded-full px-3 py-1.5 ${
              categoryId === null ? "bg-black text-white" : "bg-black/[0.05]"
            }`}
          >
            Hammasi
          </button>
          {roots.map((root) => (
            <span key={root.id} className="flex shrink-0 gap-2">
              <button
                onClick={() => setCategoryId(root.id)}
                className={`rounded-full px-3 py-1.5 ${
                  categoryId === root.id ? "bg-black text-white" : "bg-black/[0.05]"
                }`}
              >
                {root.name}
              </button>
              {childrenOf(root.id).map((child) => (
                <button
                  key={child.id}
                  onClick={() => setCategoryId(child.id)}
                  className={`rounded-full px-3 py-1.5 ${
                    categoryId === child.id ? "bg-black text-white" : "bg-black/[0.03]"
                  }`}
                >
                  {child.name}
                </button>
              ))}
            </span>
          ))}
        </nav>
      )}

      <div className="flex gap-2 px-4 pt-4">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Mahsulot qidirish"
          className="flex-1 rounded-xl bg-black/[0.04] px-4 py-2.5 text-sm outline-none placeholder:text-black/30"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-xl bg-black/[0.04] px-3 text-xs outline-none"
        >
          {SORTS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <section className="px-4 pt-4">
        {loading && <ProductGridSkeleton />}
        {!loading && error && <ErrorState message={error} onRetry={loadProducts} />}
        {!loading && !error && products?.items.length === 0 && (
          <EmptyState title="Mahsulot topilmadi" hint="Filterni o'zgartirib ko'ring" />
        )}
        {!loading && !error && products && products.items.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-3">
              {products.items.map((product) => (
                <ProductCard key={product.id} shopId={id} product={product} />
              ))}
            </div>
            <p className="mt-6 text-center text-xs text-black/35">
              {products.total} ta mahsulot
            </p>
          </>
        )}
      </section>
    </main>
  );
}
