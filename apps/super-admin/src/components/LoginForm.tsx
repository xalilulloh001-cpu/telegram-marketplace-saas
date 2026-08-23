"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

export function LoginForm({ onSuccess }: { onSuccess: () => void | Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    const res = await apiFetch("/api/v1/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setBusy(false);
    if (res.ok) {
      await onSuccess();
    } else if (res.status === 429) {
      setError("Juda ko'p urinish. Birozdan keyin qayta urinib ko'ring.");
    } else {
      setError("Email yoki parol noto'g'ri");
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-sm space-y-3">
        <h1 className="text-xl font-semibold">Super Admin</h1>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="w-full rounded border px-3 py-2 text-sm"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Parol"
          className="w-full rounded border px-3 py-2 text-sm"
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button
          onClick={submit}
          disabled={busy}
          className="w-full rounded bg-black px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? "…" : "Kirish"}
        </button>
      </div>
    </main>
  );
}
