"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { EmptyState, MemberDot, Skeleton, ThemeToggle, memberColor } from "@/components/ui";
import { getCached, setCached } from "@/lib/cache";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { Circle, User } from "@/lib/types";

const CIRCLE_THEMES = [
  { key: "cp", icon: "eye" },
  { key: "cg", icon: "users" },
  { key: "cb", icon: "globe" },
];

function circleTheme(id: string) {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) | 0;
  return CIRCLE_THEMES[Math.abs(h) % CIRCLE_THEMES.length];
}

export default function Home() {
  const ready = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [circles, setCircles] = useState<Circle[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    const cached = getCached<{ user: User; circles: Circle[] }>("me");
    if (cached) {
      setUser(cached.user);
      setCircles(cached.circles);
    }
    api.me().then(({ user, circles }) => {
      setCached("me", { user, circles });
      setUser(user);
      setCircles(circles);
    });
  }, []);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    await api.createCircle(name.trim());
    setBusy(false);
    setCreating(false);
    setName("");
    load();
  }

  if (!ready || !circles)
    return (
      <main className="py-5">
        <div className="mb-8 mt-16"><Skeleton height={96} count={3} /></div>
      </main>
    );

  const greeting = new Date().getHours() < 12 ? "Good morning" : new Date().getHours() < 17 ? "Good afternoon" : "Good evening";
  const totalIdeas = circles.reduce((n, c) => n + c.open_intent_count, 0);

  return (
    <main className="py-5">
      <div className="flex items-center justify-between">
        <div className="font-serif text-xs font-medium uppercase tracking-[.18em]" style={{ color: "var(--acc)" }}>
          Someday
        </div>
        <div className="flex items-center gap-2.5">
          <ThemeToggle />
          <Link href="/settings" aria-label="Settings"
            className="flex h-10 w-10 items-center justify-center rounded-full font-bold text-white"
            style={{ background: "var(--acc)", border: "2px solid var(--brd)", boxShadow: "0 3px 10px var(--acc-glow)" }}>
            {(user?.display_name ?? "?").charAt(0).toUpperCase()}
          </Link>
        </div>
      </div>

      <h1 className="mt-5 font-serif text-[28px] font-medium leading-tight">
        {greeting},<br />{user?.display_name ?? "friend"}.
      </h1>
      <p className="mt-1.5 text-[13px]" style={{ color: "var(--txt-m)" }}>
        {circles.length} {circles.length === 1 ? "circle" : "circles"} · {totalIdeas} ideas waiting
      </p>

      <div className="mt-6 flex flex-col gap-3.5">
        {circles.length === 0 && (
          <EmptyState message="No circles yet — start one and invite someone you keep making plans with." />
        )}
        {circles.map((c) => {
          const theme = circleTheme(c.id);
          return (
            <Link key={c.id} href={`/circles/${c.id}`}
              className="glass relative flex items-center gap-4 overflow-hidden p-4 pl-5 transition-transform active:scale-[.98]"
              style={{ borderRadius: "var(--r)", boxShadow: "var(--shc)" }}>
              <div className="absolute inset-y-0 left-0 w-1" style={{ background: `var(--${theme.key})` }} />
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl"
                style={{ background: `var(--${theme.key}-l)`, color: `var(--${theme.key})`, border: "1px solid var(--brd)" }}>
                <Icon name={theme.icon} size="lg" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate font-serif font-semibold">{c.name}</div>
                <div className="text-xs" style={{ color: "var(--txt-m)" }}>
                  {c.member_count} {c.member_count === 1 ? "member" : "members"}
                </div>
                <div className="mt-2 flex">
                  {Array.from({ length: Math.min(c.member_count, 5) }).map((_, i) => (
                    <MemberDot key={i} name={null} color={memberColor(i)} />
                  ))}
                </div>
              </div>
              <span className="whitespace-nowrap rounded-full px-3 py-1.5 text-[11px] font-semibold"
                style={{ background: `var(--${theme.key}-l)`, color: `var(--${theme.key})`, border: `1.5px solid var(--${theme.key})33` }}>
                {c.open_intent_count} {c.open_intent_count === 1 ? "idea" : "ideas"}
              </span>
            </Link>
          );
        })}
      </div>

      {creating ? (
        <form onSubmit={create} className="glass mt-5 flex flex-col gap-3 rounded-[var(--r)] p-4">
          <input
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Movie nights, school friends, the big trip…"
            className="w-full rounded-[var(--rs)] bg-transparent px-1 py-2 text-sm outline-none"
          />
          <div className="flex gap-2.5">
            <button type="submit" disabled={busy || !name.trim()} className="btn-primary flex-1 py-2.5 text-sm disabled:opacity-60">
              Create
            </button>
            <button type="button" onClick={() => setCreating(false)} className="btn-ghost px-5 py-2.5 text-sm">
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button onClick={() => setCreating(true)} className="btn-ghost mt-5 w-full py-3.5 text-sm" style={{ color: "var(--txt-m)" }}>
          <Icon name="plus" size="sm" />
          New Circle
        </button>
      )}
    </main>
  );
}
