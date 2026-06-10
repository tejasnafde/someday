"use client";

import { useState } from "react";
import { Icon } from "@/components/Sprite";
import { supabase } from "@/lib/supabase";

export default function Login() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/auth/callback` },
    });
    setBusy(false);
    if (error)
      setError(
        error.message.includes("rate limit")
          ? "Too many sign-in emails right now — wait a bit and try again."
          : error.message,
      );
    else setSent(true);
  }

  return (
    <main className="flex min-h-screen flex-col justify-center py-12">
      <div className="mb-10 text-center">
        <div className="font-serif text-xs font-medium uppercase tracking-[.18em]" style={{ color: "var(--acc)" }}>
          Someday
        </div>
        <h1 className="mt-4 font-serif text-3xl font-medium leading-tight">
          For all the things<br />you&apos;ll do together<br /><em style={{ color: "var(--acc)" }}>someday.</em>
        </h1>
      </div>

      {sent ? (
        <div className="glass rounded-[var(--r)] p-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
            <Icon name="mail" size="lg" />
          </div>
          <div className="font-semibold">Check your email</div>
          <div className="mt-1 text-sm" style={{ color: "var(--txt-m)" }}>
            We sent a sign-in link to {email}
          </div>
        </div>
      ) : (
        <form onSubmit={send} className="flex flex-col gap-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="glass w-full rounded-[var(--rs)] px-4 py-3 text-sm outline-none"
            style={{ color: "var(--txt)" }}
          />
          {error && <div className="text-sm" style={{ color: "var(--cp)" }}>{error}</div>}
          <button type="submit" disabled={busy} className="btn-primary w-full py-3.5 text-sm disabled:opacity-60">
            {busy ? "Sending…" : "Send magic link"}
          </button>
        </form>
      )}
    </main>
  );
}
