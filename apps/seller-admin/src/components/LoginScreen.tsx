"use client";

import { useCallback, useState } from "react";
import { apiFetch } from "@/lib/api";
import { TelegramLoginButton } from "@/components/TelegramLoginButton";

const BOT_USERNAME = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "";

export function LoginScreen({ onSuccess }: { onSuccess: () => void | Promise<void> }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleAuth = useCallback(
    async (user: Record<string, string | number>) => {
      setBusy(true);
      setError(null);
      // The raw widget payload goes to the server, which verifies the signature.
      const payload = Object.fromEntries(
        Object.entries(user).map(([key, value]) => [key, String(value)]),
      );
      const res = await apiFetch("/api/v1/auth/telegram/seller", {
        method: "POST",
        body: JSON.stringify({ login_widget: payload }),
      });
      setBusy(false);

      if (res.ok) {
        await onSuccess();
      } else if (res.status === 403) {
        setError("Bu Telegram hisobi hech qanday do'konga biriktirilmagan.");
      } else {
        setError("Kirish amalga oshmadi. Qayta urinib ko'ring.");
      }
    },
    [onSuccess],
  );

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <div className="w-full max-w-sm space-y-4 text-center">
        <div>
          <h1 className="text-xl font-semibold">Seller Admin</h1>
          <p className="mt-1 text-sm text-gray-500">
            Do&apos;koningizni boshqarish uchun Telegram orqali kiring.
          </p>
        </div>

        {BOT_USERNAME ? (
          <div className="flex justify-center">
            <TelegramLoginButton botUsername={BOT_USERNAME} onAuth={handleAuth} />
          </div>
        ) : (
          <p className="text-sm text-amber-600">
            NEXT_PUBLIC_TELEGRAM_BOT_USERNAME sozlanmagan.
          </p>
        )}

        {busy && <p className="text-sm text-gray-500">Tekshirilmoqda…</p>}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
    </main>
  );
}
