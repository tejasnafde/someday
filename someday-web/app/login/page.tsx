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

  async function signInWithGoogle() {
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
    if (error) { setBusy(false); setError(error.message); }
  }

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
          ? "Too many sign-in emails right now - wait a bit and try again."
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
      setError("That code didn't work - check it and try again.");
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

      {!sent && (
        <>
          <button onClick={signInWithGoogle} disabled={busy}
            className="btn-ghost flex w-full items-center justify-center gap-3 py-3.5 text-sm disabled:opacity-60">
            <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
          <div className="flex items-center gap-3">
            <div className="h-px flex-1" style={{ background: "var(--brd-s)" }} />
            <span className="text-[11px]" style={{ color: "var(--txt-l)" }}>or</span>
            <div className="h-px flex-1" style={{ background: "var(--brd-s)" }} />
          </div>
        </>
      )}

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
