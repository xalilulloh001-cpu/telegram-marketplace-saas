"use client";

import { useAdmin } from "@/components/AdminGuard";

export default function Dashboard() {
  const { admin, logout } = useAdmin();

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Super Admin</h1>
        <button onClick={logout} className="rounded border px-3 py-1 text-sm">
          Chiqish
        </button>
      </div>
      <p className="mt-4 text-sm text-gray-500">{admin?.email}</p>
    </main>
  );
}
