"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { NavBar, Spinner, ThemeToggle } from "@/components/ui";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/useAuth";
import type { User } from "@/lib/types";

export default function SettingsPage() {
  const ready = useAuth();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (ready)
      api.me().then(({ user }) => {
        setUser(user);
        setName(user.display_name ?? "");
      });
  }, [ready]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    const { user } = await api.updateMe({ display_name: name.trim() });
    setUser(user);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function signOut() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (!ready || !user) return <Spinner />;

  return (
    <main>
      <NavBar title="Settings" back="/" right={<ThemeToggle />} />

      <div className="glass flex items-center gap-4 rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
        <div className="flex h-12 w-12 items-center justify-center rounded-full font-bold text-white"
          style={{ background: "var(--acc)", boxShadow: "0 3px 10px var(--acc-glow)" }}>
          {(user.display_name ?? "?").charAt(0).toUpperCase()}
        </div>
        <div>
          <div className="font-serif font-semibold">{user.display_name}</div>
          <div className="text-xs" style={{ color: "var(--txt-m)" }}>{user.email}</div>
        </div>
      </div>

      <form onSubmit={save} className="glass mt-4 rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
        <label className="mb-2 block text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
          Display name
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-[var(--rs)] px-3.5 py-3 text-sm outline-none"
          style={{ background: "var(--glass-lo)", border: "1px solid var(--brd-h)", color: "var(--txt)" }}
        />
        <button type="submit" disabled={saving || !name.trim() || name.trim() === user.display_name}
          className="btn-primary mt-3 w-full py-3 text-sm disabled:opacity-50">
          {saved ? "Saved" : saving ? "Saving…" : "Save"}
        </button>
      </form>

      <button onClick={signOut} className="btn-ghost mt-5 w-full py-3.5 text-sm" style={{ color: "var(--cp)" }}>
        <Icon name="log-out" size="sm" />
        Sign out
      </button>
    </main>
  );
}
