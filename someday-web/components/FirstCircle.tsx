"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Sprite";
import { Tour } from "@/components/Tour";
import { api } from "@/lib/api";
import { isNativeShell } from "@/lib/nativeShell";
import type { Circle } from "@/lib/types";

/**
 * One-step onboarding for a signed-in user with zero circles: name a circle,
 * then share its invite link at once. `onCreated` lets the dashboard refresh
 * its data while this screen stays up for the invite step.
 */
export function FirstCircle({ onCreated, onSkip }: { onCreated: () => void; onSkip: () => void }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [circle, setCircle] = useState<Circle | null>(null);
  const [copied, setCopied] = useState(false);
  const [canShare, setCanShare] = useState(false);
  const [inShell, setInShell] = useState(false);
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setCanShare(typeof navigator.share === "function");
    // The Android shell's WebView cannot open wa.me in WhatsApp, but it hands
    // non-http schemes to the OS, so it gets the app scheme instead.
    setInShell(isNativeShell());
    return () => { if (copyTimer.current) clearTimeout(copyTimer.current); };
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setCircle(await api.createCircle(name.trim()));
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create circle - try again.");
    } finally {
      setBusy(false);
    }
  }

  if (!circle)
    return (
      <main className="flex min-h-[80vh] flex-col justify-center py-5">
        <h1 className="font-serif text-[28px] font-medium leading-tight">Who do you make plans with?</h1>
        <p className="mt-2 text-sm leading-6" style={{ color: "var(--txt-m)" }}>
          Name a circle for them. You can invite them next.
        </p>
        <form onSubmit={create} className="mt-6 flex flex-col gap-3">
          <input
            autoFocus
            required
            maxLength={80}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Sunday people, college gang, the Goa trip"
            aria-label="Circle name"
            className="glass w-full rounded-[var(--rs)] px-4 py-3.5 text-sm outline-none"
          />
          {error && <p className="text-xs" style={{ color: "var(--cp)" }}>{error}</p>}
          <button type="submit" disabled={busy || !name.trim()} className="btn-primary min-h-12 w-full text-sm disabled:opacity-60">
            {busy ? "Creating…" : "Create circle"}
          </button>
          <button type="button" onClick={onSkip} className="py-2 text-xs font-medium" style={{ color: "var(--txt-m)" }}>
            Skip for now
          </button>
        </form>
      </main>
    );

  const link = `${location.origin}/join/${circle.invite_token}`;
  const message = `Join "${circle.name}" on Someday so we can save the things we want to do together: ${link}`;
  const whatsapp = inShell
    ? `whatsapp://send?text=${encodeURIComponent(message)}`
    : `https://wa.me/?text=${encodeURIComponent(message)}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      if (copyTimer.current) clearTimeout(copyTimer.current);
      copyTimer.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy - press and hold the link to copy it.");
    }
  }

  function share() {
    navigator.share({ title: `Join ${circle!.name} on Someday`, text: message }).catch(() => {});
  }

  return (
    <main className="flex min-h-[80vh] flex-col justify-center py-5">
      <h1 className="font-serif text-[28px] font-medium leading-tight">Invite them to {circle.name}</h1>
      <p className="mt-2 text-sm leading-6" style={{ color: "var(--txt-m)" }}>
        Anyone with this link can join. Ideas are better when someone says yes.
      </p>
      <div data-tour="onboard-invite" className="mt-6 flex flex-col gap-3">
        <div className="break-all rounded-[var(--rs)] px-3 py-2.5 text-xs"
          style={{ background: "var(--glass-lo)", color: "var(--txt-m)", border: "1px solid var(--brd-s)" }}>
          {link}
        </div>
        <a href={whatsapp} target="_blank" rel="noreferrer" className="btn-primary min-h-12 w-full text-sm">
          <Icon name="message-circle" size="sm" />
          Share on WhatsApp
        </a>
        <div className="flex gap-2.5">
          <button onClick={copy} className="btn-ghost min-h-11 flex-1 text-sm">
            <Icon name={copied ? "check" : "copy"} size="sm" />
            {copied ? "Copied" : "Copy link"}
          </button>
          {canShare && (
            <button onClick={share} className="btn-ghost min-h-11 flex-1 text-sm">
              <Icon name="link" size="sm" />
              Other apps
            </button>
          )}
        </div>
        {error && <p className="text-xs" style={{ color: "var(--cp)" }}>{error}</p>}
      </div>
      <Link href={`/circles/${circle.id}`} className="mt-6 py-2 text-center text-sm font-medium" style={{ color: "var(--acc)" }}>
        Go to {circle.name}
      </Link>
      <Tour page="onboarding" />
    </main>
  );
}
