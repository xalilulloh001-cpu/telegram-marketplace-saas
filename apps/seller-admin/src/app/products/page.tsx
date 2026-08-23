"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, type Category, type Page, type Product } from "@/lib/api";

const SORTS = [
  ["newest", "Yangi"],
  ["price_asc", "Narx ↑"],
  ["price_desc", "Narx ↓"],
  ["name_asc", "Nom A-Z"],
] as const;

export default function ProductsPage() {
  const [page, setPage] = useState<Page<Product> | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [pageNum, setPageNum] = useState(1);
  const [form, setForm] = useState({ name: "", price: "", stock: "0", category_id: "" });
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    const params = new URLSearchParams({ page: String(pageNum), page_size: "20", sort });
    if (search) params.set("search", search);
    return apiFetch(`/api/v1/seller/products?${params}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: Page<Product> | null) => setPage(data));
  }, [pageNum, search, sort]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    apiFetch("/api/v1/seller/categories?page_size=100")
      .then((res) => (res.ok ? res.json() : null))
      .then((data: Page<Category> | null) => setCategories(data?.items ?? []));
  }, []);

  const create = async () => {
    setError(null);
    const res = await apiFetch("/api/v1/seller/products", {
      method: "POST",
      body: JSON.stringify({
        name: form.name,
        price: form.price,
        stock: Number(form.stock),
        category_id: form.category_id ? Number(form.category_id) : null,
      }),
    });
    if (res.ok) {
      setForm({ name: "", price: "", stock: "0", category_id: "" });
      await load();
    } else {
      setError("Mahsulot yaratilmadi — maydonlarni tekshiring");
    }
  };

  const remove = async (id: number) => {
    await apiFetch(`/api/v1/seller/products/${id}`, { method: "DELETE" });
    await load();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Mahsulotlar</h1>

      <div className="grid gap-2 rounded border bg-white p-4 sm:grid-cols-5">
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nomi"
          className="rounded border px-3 py-2 text-sm sm:col-span-2"
        />
        <input
          value={form.price}
          onChange={(e) => setForm({ ...form, price: e.target.value })}
          placeholder="Narx"
          inputMode="decimal"
          className="rounded border px-3 py-2 text-sm"
        />
        <input
          value={form.stock}
          onChange={(e) => setForm({ ...form, stock: e.target.value })}
          placeholder="Qoldiq"
          inputMode="numeric"
          className="rounded border px-3 py-2 text-sm"
        />
        <select
          value={form.category_id}
          onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          className="rounded border px-3 py-2 text-sm"
        >
          <option value="">Kategoriyasiz</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          onClick={create}
          className="rounded bg-black px-4 py-2 text-sm text-white sm:col-span-5"
        >
          Mahsulot qo&apos;shish
        </button>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex gap-2">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPageNum(1);
          }}
          placeholder="Qidirish…"
          className="flex-1 rounded border px-3 py-2 text-sm"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded border px-3 py-2 text-sm"
        >
          {SORTS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <ul className="divide-y rounded border bg-white">
        {page?.items.map((p) => (
          <li key={p.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>
              {p.name} — {p.price} · {p.stock} dona
              {!p.is_active && <span className="ml-2 text-gray-400">(nofaol)</span>}
            </span>
            <button onClick={() => remove(p.id)} className="text-red-500">
              O&apos;chirish
            </button>
          </li>
        ))}
        {page?.items.length === 0 && (
          <li className="px-4 py-3 text-sm text-gray-500">Mahsulot topilmadi</li>
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
