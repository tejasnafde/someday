"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Sprite";
import { NavBar, Spinner, ThemeToggle } from "@/components/ui";
import { api } from "@/lib/api";
import { getCached, setCached } from "@/lib/cache";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/useAuth";
import type { Circle, User } from "@/lib/types";

export default function SettingsPage() {
  const ready = useAuth();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (ready) api.me().then(({ user }) => setUser(user));
  }, [ready]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  function startEdit() {
    setName(user?.display_name ?? "");
    setEditing(true);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || trimmed === user?.display_name) {
      setEditing(false);
      return;
    }
    setSaving(true);
    const { user: updated } = await api.updateMe({ display_name: trimmed });
    setUser(updated);
    setSaving(false);
    setEditing(false);
  }

  async function signOut() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  async function replayTour() {
    await api.tourReset();
    localStorage.removeItem("tour:pending");
    const me = getCached<{ user: User; circles: Circle[] }>("me");
    if (me?.user) setCached("me", { ...me, user: { ...me.user, tour_state: { seen: [] } } });
    router.push("/");
  }

  if (!ready || !user) return <Spinner />;

  return (
    <main>
      <NavBar title="Settings" back="/" right={<ThemeToggle />} />

      <div className="glass flex items-center gap-4 rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full font-bold text-white"
          style={{ background: "var(--acc)", boxShadow: "0 3px 10px var(--acc-glow)" }}>
          {(user.display_name ?? "?").charAt(0).toUpperCase()}
        </div>

        {editing ? (
          <form onSubmit={save} className="flex min-w-0 flex-1 items-center gap-2">
            <input
              ref={inputRef}
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setEditing(false)}
              className="min-w-0 flex-1 rounded-[var(--rs)] px-3 py-2 font-serif font-semibold outline-none"
              style={{ background: "var(--glass-lo)", border: "1px solid var(--acc)", color: "var(--txt)" }}
            />
            <button type="submit" disabled={saving} aria-label="Save name"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white disabled:opacity-50"
              style={{ background: "var(--acc)" }}>
              <Icon name="check" size="sm" />
            </button>
            <button type="button" onClick={() => setEditing(false)} aria-label="Cancel"
              className="glass flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
              style={{ color: "var(--txt-m)" }}>
              <Icon name="x" size="sm" />
            </button>
          </form>
        ) : (
          <>
            <div className="min-w-0 flex-1">
              <div className="truncate font-serif font-semibold">{user.display_name}</div>
              <div className="truncate text-xs" style={{ color: "var(--txt-m)" }}>{user.email}</div>
            </div>
            <button onClick={startEdit} aria-label="Edit name"
              className="glass flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
              style={{ color: "var(--txt-m)" }}>
              <Icon name="pencil" size="sm" />
            </button>
          </>
        )}
      </div>

      <button onClick={replayTour} className="btn-ghost mt-5 w-full py-3.5 text-sm" style={{ color: "var(--txt-m)" }}>
        <Icon name="target" size="sm" />
        Replay tour
      </button>

      <button onClick={signOut} className="btn-ghost mt-3 w-full py-3.5 text-sm" style={{ color: "var(--cp)" }}>
        <Icon name="log-out" size="sm" />
        Sign out
      </button>
    </main>
  );
}
