"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, setAccessToken } from "@/lib/api";
import { getTelegramWebApp } from "@/lib/telegram";

type Customer = { telegram_id: number; customer_id: number };
type AuthState = {
  customer: Customer | null;
  status: "loading" | "authenticated" | "unauthenticated";
  error: string | null;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState>({
  customer: null,
  status: "loading",
  error: null,
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tg = getTelegramWebApp();
    tg?.ready();
    // Every state update happens in a promise callback so the effect body stays synchronous-free.
    // The raw initData goes to the server, which verifies its signature; the returned
    // token lives in memory only — never localStorage.
    const request = tg?.initData
      ? apiFetch("/api/v1/auth/telegram", {
          method: "POST",
          body: JSON.stringify({ init_data: tg.initData }),
        })
      : Promise.reject(new Error("Telegram Mini App ichida oching"));

    request
      .then(async (res) => {
        if (!res.ok) throw new Error("Autentifikatsiya amalga oshmadi");
        const data = await res.json();
        setAccessToken(data.access_token);
        setCustomer({ telegram_id: data.telegram_id, customer_id: data.customer_id });
        setStatus("authenticated");
      })
      .catch((err: Error) => {
        setError(err.message);
        setStatus("unauthenticated");
      });
  }, []);

  const logout = useCallback(async () => {
    await apiFetch("/api/v1/auth/logout", { method: "POST" });
    setAccessToken(null);
    setCustomer(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ customer, status, error, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
