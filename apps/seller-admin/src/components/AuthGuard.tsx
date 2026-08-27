"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { LoginScreen } from "@/components/LoginScreen";

type Shop = { id: number; name: string; slug: string; role: string };
type SellerState = {
  shop: Shop | null;
  permissions: string[];
  status: "loading" | "authenticated" | "unauthenticated";
  logout: () => Promise<void>;
};

const SellerContext = createContext<SellerState>({
  shop: null,
  permissions: [],
  status: "loading",
  logout: async () => {},
});

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const [shop, setShop] = useState<Shop | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [status, setStatus] = useState<SellerState["status"]>("loading");

  const refresh = useCallback(
    () =>
      apiFetch("/api/v1/auth/me")
        .then(async (res) => {
          if (!res.ok) throw new Error("unauthenticated");
          const data = await res.json();
          if (data.principal_type !== "seller") throw new Error("not a seller");
          setShop(data.shop ?? null);
          setPermissions(data.permissions ?? []);
          setStatus("authenticated");
        })
        .catch(() => setStatus("unauthenticated")),
    [],
  );

  useEffect(() => {
    apiFetch("/api/v1/auth/me")
      .then(async (res) => {
        if (!res.ok) throw new Error("unauthenticated");
        const data = await res.json();
        if (data.principal_type !== "seller") throw new Error("not a seller");
        setShop(data.shop ?? null);
        setPermissions(data.permissions ?? []);
        setStatus("authenticated");
      })
      .catch(() => setStatus("unauthenticated"));
  }, []);

  const logout = useCallback(async () => {
    await apiFetch("/api/v1/auth/logout", { method: "POST" });
    setShop(null);
    setStatus("unauthenticated");
  }, []);

  if (status === "loading") {
    return <p className="p-8 text-sm text-gray-500">Tekshirilmoqda…</p>;
  }

  if (status === "unauthenticated") {
    return <LoginScreen onSuccess={refresh} />;
  }

  return (
    <SellerContext.Provider value={{ shop, permissions, status, logout }}>
      {children}
    </SellerContext.Provider>
  );
}

export const useSeller = () => useContext(SellerContext);
