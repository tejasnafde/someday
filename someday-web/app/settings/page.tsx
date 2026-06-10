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

  useEffect(() => {
    if (ready) api.me().then(({ user }) => setUser(user));
  }, [ready]);

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

      <button onClick={signOut} className="btn-ghost mt-5 w-full py-3.5 text-sm" style={{ color: "var(--cp)" }}>
        <Icon name="log-out" size="sm" />
        Sign out
      </button>
    </main>
  );
}
