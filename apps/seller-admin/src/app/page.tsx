"use client";

import { useSeller } from "@/components/AuthGuard";

export default function Dashboard() {
  const { shop, permissions, logout } = useSeller();

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{shop?.name ?? "Do'kon"}</h1>
        <button onClick={logout} className="rounded border px-3 py-1 text-sm">
          Chiqish
        </button>
      </div>
      <p className="text-sm text-gray-500">Rol: {shop?.role}</p>
      <p className="mt-2 text-sm text-gray-500">Ruxsatlar: {permissions.length}</p>
    </main>
  );
}
