"use client";

import { useAuth } from "@/components/AuthProvider";

export default function Home() {
  const { customer, status, error, logout } = useAuth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-8">
      <h1 className="text-2xl font-semibold">Marketplace</h1>
      {status === "loading" && <p className="text-sm text-gray-500">Tekshirilmoqda…</p>}
      {status === "unauthenticated" && <p className="text-sm text-red-500">{error}</p>}
      {status === "authenticated" && customer && (
        <>
          <p className="text-sm text-gray-600">Telegram ID: {customer.telegram_id}</p>
          <button onClick={logout} className="rounded border px-3 py-1 text-sm">
            Chiqish
          </button>
        </>
      )}
    </main>
  );
}
