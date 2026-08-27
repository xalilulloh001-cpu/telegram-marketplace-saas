"use client";

import { useEffect, useRef } from "react";

type TelegramUser = Record<string, string | number>;

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramUser) => void;
  }
}

export function TelegramLoginButton({
  botUsername,
  onAuth,
}: {
  botUsername: string;
  onAuth: (user: TelegramUser) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // The widget calls a global function by name, so it is registered before the
    // script is injected and removed on unmount.
    window.onTelegramAuth = onAuth;

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "8");
    script.setAttribute("data-userpic", "false");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");

    const container = containerRef.current;
    container?.appendChild(script);

    return () => {
      delete window.onTelegramAuth;
      if (container) container.innerHTML = "";
    };
  }, [botUsername, onAuth]);

  return <div ref={containerRef} />;
}
