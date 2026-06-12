"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Icon } from "@/components/Sprite";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
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

  async function verifyCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.verifyOtp({ email, token: code.trim(), type: "email" });
    if (error) {
      setBusy(false);
      setError("That code didn't work — check it and try again.");
      return;
    }
    await api.verify().catch(() => {});
    const next = sessionStorage.getItem("next") ?? "/";
    sessionStorage.removeItem("next");
    router.replace(next);
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
        <div className="flex flex-col gap-4">
          <div className="glass rounded-[var(--r)] p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
              <Icon name="mail" size="lg" />
            </div>
            <div className="font-semibold">Check your email</div>
            <div className="mt-1 text-sm" style={{ color: "var(--txt-m)" }}>
              Tap the link, or enter the code below.
            </div>
          </div>

          <form onSubmit={verifyCode} className="flex flex-col gap-3">
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={10}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Code from the email"
              className="glass w-full rounded-[var(--rs)] px-4 py-3 text-center text-lg tracking-[.3em] outline-none"
              style={{ color: "var(--txt)" }}
            />
            {error && <div className="text-center text-sm" style={{ color: "var(--cp)" }}>{error}</div>}
            <button type="submit" disabled={busy || code.trim().length < 6} className="btn-primary w-full py-3.5 text-sm disabled:opacity-60">
              {busy ? "Signing in…" : "Sign in with code"}
            </button>
            <button type="button" onClick={() => { setSent(false); setCode(""); setError(""); }}
              className="text-center text-sm" style={{ color: "var(--txt-m)" }}>
              Different email
            </button>
          </form>
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
