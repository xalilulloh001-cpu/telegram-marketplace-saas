export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Sessions ride in an httpOnly cookie, so every call must include credentials
// and no token is ever readable from JavaScript.
export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type Category = {
  id: number;
  name: string;
  slug: string;
  parent_id: number | null;
  is_active: boolean;
};

export type Product = {
  id: number;
  name: string;
  slug: string;
  price: string;
  discount_price: string | null;
  stock: number;
  is_active: boolean;
  category_id: number | null;
};

export type Shop = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  contact_phone: string | null;
  city: string | null;
};
