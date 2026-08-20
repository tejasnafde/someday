"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { Tour } from "@/components/Tour";
import { CircleAvatar, EmptyState, MemberDot, Skeleton, ThemeToggle, circleTheme, memberColor } from "@/components/ui";
import { getCached, setCached } from "@/lib/cache";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { Circle, User } from "@/lib/types";

function PublicLanding() {
  const steps = [
    {
      icon: "users",
      title: "Create a circle",
      copy: "Bring together the people you keep making plans with.",
    },
    {
      icon: "heart",
      title: "Save what sounds good",
      copy: "Add the films, trips, meals, and small plans you want to remember.",
    },
    {
      icon: "check",
      title: "Choose a real someday",
      copy: "See what everyone wants, make a plan, and keep the memory when it happens.",
    },
  ];

  return (
    <main className="flex min-h-screen flex-col py-5">
      <nav className="flex items-center justify-between" aria-label="Primary">
        <a href="#top" className="font-serif text-xs font-medium uppercase tracking-[.18em]" style={{ color: "var(--acc)" }}>
          Someday
        </a>
        <div className="flex items-center gap-2.5">
          <ThemeToggle />
          <Link href="/login" className="btn-ghost min-h-11 px-4 text-sm">
            Sign in
          </Link>
        </div>
      </nav>

      <section id="top" className="flex min-h-[70vh] flex-col justify-center py-16 text-center">
        <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-[18px] text-white"
          style={{ background: "linear-gradient(135deg, var(--acc), var(--acc-m))", boxShadow: "var(--shb)" }}>
          <Icon name="star" size="lg" />
        </div>
        <h1 className="font-serif text-[42px] font-medium leading-[1.08] tracking-[-.025em]">
          Save the things you want to do together.
        </h1>
        <p className="mx-auto mt-5 max-w-sm text-[15px] leading-7" style={{ color: "var(--txt-m)" }}>
          Someday keeps recommendations, plans, and small promises in one shared place, until you are ready to make them happen.
        </p>
        <Link href="/login" className="btn-primary mx-auto mt-8 min-h-12 w-full max-w-xs px-6 text-sm">
          Create your first circle
        </Link>
        <a href="#how-it-works" className="mt-4 text-xs font-medium" style={{ color: "var(--txt-m)" }}>
          See how it works
        </a>
      </section>

      <section id="how-it-works" className="pb-16 pt-6">
        <div className="mb-5">
          <div className="text-[11px] font-semibold uppercase tracking-[.16em]" style={{ color: "var(--acc)" }}>
            How it works
          </div>
          <h2 className="mt-2 font-serif text-2xl font-medium">From “we should” to “we did.”</h2>
        </div>
        <ol className="flex flex-col gap-3.5">
          {steps.map((step, index) => (
            <li key={step.title} className="glass flex gap-4 rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px]"
                style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
                <Icon name={step.icon} />
              </div>
              <div className="min-w-0 pt-0.5">
                <div className="flex items-baseline gap-2">
                  <span className="tnum text-[10px] font-semibold" style={{ color: "var(--txt-l)" }}>0{index + 1}</span>
                  <h3 className="font-serif text-base font-semibold">{step.title}</h3>
                </div>
                <p className="mt-1 text-[13px] leading-5" style={{ color: "var(--txt-m)" }}>{step.copy}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="glass-hi rounded-[var(--r)] p-6 text-center" style={{ boxShadow: "var(--shc)" }}>
        <h2 className="font-serif text-2xl font-medium">What have you been meaning to do?</h2>
        <p className="mt-2 text-sm leading-6" style={{ color: "var(--txt-m)" }}>
          Start a circle, invite someone, and save the first thing you keep saying you will do.
        </p>
        <Link href="/login" className="btn-primary mt-5 min-h-12 w-full px-6 text-sm">
          Start with Someday
        </Link>
      </section>

      <footer className="flex items-center justify-between py-8 text-[11px]" style={{ color: "var(--txt-l)" }}>
        <span>Someday</span>
        <a href="https://tn07.dev/" className="underline decoration-transparent underline-offset-4 hover:decoration-current">
          Built by Tejas Nafde
        </a>
      </footer>
    </main>
  );
}

export default function Home() {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [circles, setCircles] = useState<Circle[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [unseen, setUnseen] = useState(0);

  const load = useCallback(() => {
    const cached = getCached<{ user: User; circles: Circle[] }>("me");
    if (cached) {
      setUser(cached.user);
      setCircles(cached.circles);
    }
    api
      .me()
      .catch(async () => {
        // Session exists but no account row yet (e.g. signup link landed on
        // the root instead of /auth/callback) - register, then retry.
        await api.verify();
        return api.me();
      })
      .then(({ user, circles }) => {
        setCached("me", { user, circles });
        setUser(user);
        setCircles(circles);
      })
      .catch(() => {
        setUser(null);
        setCircles(null);
      })
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      if (data.session) load();
      else setReady(true);
    });
    return () => { active = false; };
  }, [load]);

  useEffect(() => {
    if (!user) return;
    api.notifications().then((feed) => setUnseen(feed.unseen)).catch(() => {});
  }, [user]);

  const [createError, setCreateError] = useState("");

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setCreateError("");
    try {
      await api.createCircle(name.trim());
      setCreating(false);
      setName("");
      load();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Could not create circle - try again.");
    } finally {
      setBusy(false);
    }
  }

  if (!ready)
    return <PublicLanding />;

  if (!user)
    return <PublicLanding />;

  if (!circles)
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
        <div data-tour="logo" className="font-serif text-xs font-medium uppercase tracking-[.18em]" style={{ color: "var(--acc)" }}>
          Someday
        </div>
        <div className="flex items-center gap-2.5">
          <ThemeToggle />
          <Link href="/notifications" aria-label="Notifications" data-tour="notifications-bell"
            className="relative glass flex h-9 w-9 items-center justify-center rounded-full"
            style={{ color: "var(--txt-m)" }}>
            <Icon name="bell" size="sm" />
            {unseen > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white"
                style={{ background: "var(--acc)" }}>
                {unseen > 9 ? "9+" : unseen}
              </span>
            )}
          </Link>
          <Link href="/settings" aria-label="Settings" data-tour="settings"
            className="flex h-10 w-10 items-center justify-center rounded-full font-bold text-white"
            style={{ background: "var(--acc)", border: "2px solid var(--brd)", boxShadow: "0 3px 10px var(--acc-glow)" }}>
            {(user?.display_name ?? "?").charAt(0).toUpperCase()}
          </Link>
        </div>
      </div>

      <h1 className="mt-5 font-serif text-[28px] font-medium leading-tight">
        {greeting},<br />{user?.display_name ?? "friend"}.
      </h1>
      <p className="tnum mt-1.5 text-[13px]" style={{ color: "var(--txt-m)" }}>
        {circles.length} {circles.length === 1 ? "circle" : "circles"} · {totalIdeas} ideas waiting
      </p>

      <div className="mt-6 flex flex-col gap-3.5">
        {circles.length === 0 && (
          <EmptyState message="No circles yet - start one and invite someone you keep making plans with." />
        )}
        {circles.map((c) => {
          const theme = circleTheme(c.id);
          return (
            <Link key={c.id} href={`/circles/${c.id}`}
              className="glass relative flex items-center gap-4 overflow-hidden p-4 transition-transform active:scale-[.96]"
              style={{ borderRadius: "var(--r)", boxShadow: "var(--shc)" }}>
              <CircleAvatar circleId={c.id} themeKey={theme.key} icon={theme.icon} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-serif font-semibold">{c.name}</div>
                <div className="tnum text-xs" style={{ color: "var(--txt-m)" }}>
                  {c.member_count} {c.member_count === 1 ? "member" : "members"}
                </div>
                <div className="mt-2 flex">
                  {Array.from({ length: Math.min(c.member_count, 5) }).map((_, i) => (
                    <MemberDot key={i} name={null} color={memberColor(i)} />
                  ))}
                </div>
              </div>
              <span className="tnum whitespace-nowrap rounded-full px-3 py-1.5 text-[11px] font-semibold"
                style={{ background: "var(--glass-lo)", color: "var(--txt-m)" }}>
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
          {createError && <p className="text-xs" style={{ color: "var(--cp)" }}>{createError}</p>}
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
        <button onClick={() => setCreating(true)} data-tour="create-circle" className="btn-ghost mt-5 w-full py-3.5 text-sm" style={{ color: "var(--txt-m)" }}>
          <Icon name="plus" size="sm" />
          New Circle
        </button>
      )}

      <Tour page="dashboard" />
    </main>
  );
}
