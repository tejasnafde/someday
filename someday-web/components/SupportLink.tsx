"use client";

import { useEffect, useState } from "react";
import { isNativeShell } from "@/lib/nativeShell";

const KOFI_URL = process.env.NEXT_PUBLIC_KOFI_URL;

/**
 * Voluntary Ko-fi tip link, web only. Store payment rules (Apple 3.1.1, Google
 * Play payments) forbid an external tip link inside a store build, and the app
 * is this web app in a WebView, so the shell mark decides. Hidden until mount:
 * the server render cannot see the user agent, and the shell must never get
 * even a flash of the link. Renders nothing when NEXT_PUBLIC_KOFI_URL is unset.
 */
export function SupportLink({ className = "", tour }: { className?: string; tour?: string }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    setShow(Boolean(KOFI_URL) && !isNativeShell());
  }, []);

  if (!show) return null;
  return (
    <a href={KOFI_URL} target="_blank" rel="noopener noreferrer" data-tour={tour}
      className={`underline decoration-transparent underline-offset-4 hover:decoration-current ${className}`}>
      Support Someday
    </a>
  );
}
