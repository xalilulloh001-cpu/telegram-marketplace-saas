"use client";

import { useEffect, useState } from "react";
import { apiFetch, type Shop } from "@/lib/api";
import { useSeller } from "@/components/AuthGuard";

export default function Dashboard() {
  const { permissions } = useSeller();
  const [shop, setShop] = useState<Shop | null>(null);
  const [saving, setSaving] = useState(false);
  const canEdit = permissions.includes("shop:settings:write");

  useEffect(() => {
    apiFetch("/api/v1/seller/shop")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setShop(data))
      .catch(() => setShop(null));
  }, []);

  const save = async () => {
    if (!shop) return;
    setSaving(true);
    const res = await apiFetch("/api/v1/seller/shop", {
      method: "PATCH",
      body: JSON.stringify({
        name: shop.name,
        description: shop.description,
        contact_phone: shop.contact_phone,
        city: shop.city,
      }),
    });
    setSaving(false);
    if (res.ok) setShop(await res.json());
  };

  if (!shop) return <p className="text-sm text-gray-500">Yuklanmoqda…</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Do&apos;kon sozlamalari</h1>
      <div className="space-y-3 rounded border bg-white p-4">
        {(
          [
            ["name", "Nomi"],
            ["description", "Tavsif"],
            ["contact_phone", "Telefon"],
            ["city", "Shahar"],
          ] as const
        ).map(([field, label]) => (
          <label key={field} className="block text-sm">
            <span className="text-gray-500">{label}</span>
            <input
              value={shop[field] ?? ""}
              disabled={!canEdit}
              onChange={(e) => setShop({ ...shop, [field]: e.target.value })}
              className="mt-1 w-full rounded border px-3 py-2 disabled:bg-gray-100"
            />
          </label>
        ))}
        {canEdit ? (
          <button
            onClick={save}
            disabled={saving}
            className="rounded bg-black px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {saving ? "…" : "Saqlash"}
          </button>
        ) : (
          <p className="text-sm text-gray-500">Sozlamalarni o&apos;zgartirish huquqingiz yo&apos;q.</p>
        )}
      </div>
    </div>
  );
}
