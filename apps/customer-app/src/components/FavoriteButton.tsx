"use client";

import { useState } from "react";
import { apiSend } from "@/lib/api";

export function FavoriteButton({
  productId,
  initial = false,
  size = "sm",
}: {
  productId: number;
  initial?: boolean;
  size?: "sm" | "lg";
}) {
  const [active, setActive] = useState(initial);
  const [busy, setBusy] = useState(false);

  const toggle = async (event: React.MouseEvent) => {
    // The button lives inside a product link, so the tap must not navigate.
    event.preventDefault();
    event.stopPropagation();
    if (busy) return;

    const next = !active;
    setActive(next); // optimistic
    setBusy(true);
    try {
      await apiSend(`/api/v1/customer/favorites/${productId}`, next ? "PUT" : "DELETE");
    } catch {
      setActive(!next); // reconcile with the server on failure
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      onClick={toggle}
      aria-label={active ? "Sevimlilardan olib tashlash" : "Sevimlilarga qo'shish"}
      className={`flex items-center justify-center rounded-full bg-white/90 shadow-sm backdrop-blur transition active:scale-90 ${
        size === "lg" ? "h-10 w-10 text-xl" : "h-8 w-8 text-sm"
      }`}
    >
      <span className={active ? "text-red-500" : "text-black/25"}>{active ? "♥" : "♡"}</span>
    </button>
  );
}
