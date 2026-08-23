import type { Metadata } from "next";
import { AdminGuard } from "@/components/AdminGuard";
import "./globals.css";

export const metadata: Metadata = {
  title: "Marketplace — Super Admin",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz">
      <body>
        <AdminGuard>{children}</AdminGuard>
      </body>
    </html>
  );
}
