"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, type Category, type Page } from "@/lib/api";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [parentId, setParentId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      apiFetch("/api/v1/seller/categories?page_size=100")
        .then((res) => (res.ok ? res.json() : null))
        .then((data: Page<Category> | null) => setCategories(data?.items ?? [])),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const create = async () => {
    setError(null);
    const res = await apiFetch("/api/v1/seller/categories", {
      method: "POST",
      body: JSON.stringify({ name, parent_id: parentId ? Number(parentId) : null }),
    });
    if (res.ok) {
      setName("");
      setParentId("");
      await load();
    } else {
      setError("Kategoriya yaratilmadi");
    }
  };

  const remove = async (id: number) => {
    const res = await apiFetch(`/api/v1/seller/categories/${id}`, { method: "DELETE" });
    if (res.status === 409) {
      setError("Bu kategoriyada mahsulot yoki ichki kategoriya bor");
    } else {
      await load();
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Kategoriyalar</h1>

      <div className="flex flex-wrap gap-2 rounded border bg-white p-4">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Kategoriya nomi"
          className="flex-1 rounded border px-3 py-2 text-sm"
        />
        <select
          value={parentId}
          onChange={(e) => setParentId(e.target.value)}
          className="rounded border px-3 py-2 text-sm"
        >
          <option value="">Asosiy kategoriya</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button onClick={create} className="rounded bg-black px-4 py-2 text-sm text-white">
          Qo&apos;shish
        </button>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <ul className="divide-y rounded border bg-white">
        {categories.map((c) => (
          <li key={c.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>
              {c.parent_id ? "— " : ""}
              {c.name} <span className="text-gray-400">/{c.slug}</span>
            </span>
            <button onClick={() => remove(c.id)} className="text-red-500">
              O&apos;chirish
            </button>
          </li>
        ))}
        {categories.length === 0 && (
          <li className="px-4 py-3 text-sm text-gray-500">Hali kategoriya yo&apos;q</li>
        )}
      </ul>
    </div>
  );
}
