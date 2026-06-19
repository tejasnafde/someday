"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    api.clientError("web_error", error.message, error.digest).catch(() => {});
  }, [error]);

  return (
    <main className="flex flex-col items-center justify-center gap-4 py-20 text-center">
      <p className="text-sm" style={{ color: "var(--cp)" }}>Something went wrong.</p>
      <button onClick={reset} className="btn-ghost px-5 py-2.5 text-sm">
        Try again
      </button>
    </main>
  );
}
