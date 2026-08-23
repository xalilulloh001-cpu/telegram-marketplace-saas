import type { Metadata } from "next";
import { AuthGuard } from "@/components/AuthGuard";
import "./globals.css";

export const metadata: Metadata = {
  title: "Marketplace — Seller Admin",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz">
      <body>
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}
