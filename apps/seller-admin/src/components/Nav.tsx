"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSeller } from "@/components/AuthGuard";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/categories", label: "Kategoriyalar" },
  { href: "/products", label: "Mahsulotlar" },
];

export function Nav() {
  const pathname = usePathname();
  const { shop, logout } = useSeller();

  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-center gap-4">
          <span className="font-semibold">{shop?.name ?? "Do'kon"}</span>
          <nav className="flex gap-3 text-sm">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={pathname === link.href ? "font-medium underline" : "text-gray-500"}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <button onClick={logout} className="rounded border px-3 py-1 text-sm">
          Chiqish
        </button>
      </div>
    </header>
  );
}
