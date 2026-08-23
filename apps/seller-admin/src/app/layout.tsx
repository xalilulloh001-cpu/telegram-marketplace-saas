import type { Metadata } from "next";
import { AuthGuard } from "@/components/AuthGuard";
import { Nav } from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Marketplace — Seller Admin",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz">
      <body className="bg-gray-50 text-gray-900">
        <AuthGuard>
          <Nav />
          <div className="mx-auto max-w-4xl px-6 py-6">{children}</div>
        </AuthGuard>
      </body>
    </html>
  );
}
