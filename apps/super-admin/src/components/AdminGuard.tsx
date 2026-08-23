"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { LoginForm } from "@/components/LoginForm";

type Admin = { id: number; email: string };
type AdminState = {
  admin: Admin | null;
  logout: () => Promise<void>;
};

const AdminContext = createContext<AdminState>({ admin: null, logout: async () => {} });

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [status, setStatus] = useState<"loading" | "in" | "out">("loading");

  const refresh = useCallback(
    () =>
      apiFetch("/api/v1/admin/auth/me").then(async (res) => {
        if (res.ok) {
          setAdmin(await res.json());
          setStatus("in");
        } else {
          setAdmin(null);
          setStatus("out");
        }
      }),
    [],
  );

  useEffect(() => {
    apiFetch("/api/v1/admin/auth/me")
      .then(async (res) => {
        if (res.ok) {
          setAdmin(await res.json());
          setStatus("in");
        } else {
          setStatus("out");
        }
      })
      .catch(() => setStatus("out"));
  }, []);

  const logout = useCallback(async () => {
    await apiFetch("/api/v1/admin/auth/logout", { method: "POST" });
    setAdmin(null);
    setStatus("out");
  }, []);

  if (status === "loading") return <p className="p-8 text-sm text-gray-500">Tekshirilmoqda…</p>;
  if (status === "out") return <LoginForm onSuccess={refresh} />;

  return <AdminContext.Provider value={{ admin, logout }}>{children}</AdminContext.Provider>;
}

export const useAdmin = () => useContext(AdminContext);
