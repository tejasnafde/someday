"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { Tour } from "@/components/Tour";
import { CircleAvatar, EmptyState, IntentCard, MemberDot, Skeleton, ThemeToggle, circleTheme, memberColor } from "@/components/ui";
import { getCached, setCached } from "@/lib/cache";
import { APK_URL, useInstallPlatform } from "@/lib/useInstallPlatform";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { Circle, Intent, User } from "@/lib/types";

// Sample circle for the landing preview. Static demo data rendered with the
// real components, so the preview cannot drift from what the app looks like.
const DEMO_STAMP = "2026-09-01T00:00:00Z";
const DEMO_MEMBERS = ["Asha", "Rohan", "Meera", "Kabir"];

function demoIntent(fields: Partial<Intent> & Pick<Intent, "id" | "title" | "category">): Intent {
  return {
    circle_id: "demo", created_by: "demo", url: null, note: null, tags: [], task_status: "saved",
    link_meta: null, planned_for: null, reaction_count: 0, boosted_by_me: false, reacted_by_me: false,
    done_note: null, done_photos: null, created_at: DEMO_STAMP, updated_at: DEMO_STAMP,
    ...fields,
  };
}

const DEMO_SAVED = [
  demoIntent({ id: "d1", title: "Past Lives, on a weeknight", category: "watch", tags: ["film night"], reaction_count: 3, reacted_by_me: true }),
  demoIntent({ id: "d2", title: "Dosa breakfast at Vidyarthi Bhavan", category: "eat", tags: ["early start"], task_status: "interested", reaction_count: 2 }),
];

const DEMO_SHORTLIST = [
  { title: "Nandi Hills for sunrise", icon: "map-pin", count: 4 },
  { title: "Learn one board game properly", icon: "gamepad", count: 3 },
];

const DEMO_DONE = demoIntent({
  id: "d3", title: "Kabini, the long weekend", category: "trip", task_status: "done",
  reaction_count: 4, done_note: "Rained the whole first day. Best trip we have taken.",
});

function DemoLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 mt-5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[.12em]" style={{ color: "var(--txt-l)" }}>
      {children}
    </div>
  );
}

function CirclePreview() {
  return (
    <div inert className="glass select-none rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
          style={{ background: "var(--cg-l)", color: "var(--cg)", border: "1px solid var(--brd)" }}>
          <Icon name="users" size="lg" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate font-serif font-semibold">Sunday people</div>
          <div className="tnum text-xs" style={{ color: "var(--txt-m)" }}>4 members · 9 ideas</div>
        </div>
        <div className="flex pr-1">
          {DEMO_MEMBERS.map((name, i) => <MemberDot key={name} name={name} color={memberColor(i)} />)}
        </div>
      </div>

      <DemoLabel>Saved</DemoLabel>
      <div className="flex flex-col gap-3">
        {DEMO_SAVED.map((intent) => <IntentCard key={intent.id} intent={intent} />)}
      </div>

      <DemoLabel><Icon name="star" size="sm" />Shortlist</DemoLabel>
      <div className="flex flex-col gap-2">
        {DEMO_SHORTLIST.map((item) => (
          <div key={item.title} className="flex items-center gap-3 rounded-[var(--rs)] px-3 py-2.5"
            style={{ background: "var(--glass-lo)", border: "1px solid var(--brd-s)" }}>
            <span style={{ color: "var(--acc)" }}><Icon name={item.icon} size="sm" /></span>
            <span className="min-w-0 flex-1 truncate font-serif text-sm font-semibold">{item.title}</span>
            <span className="tnum flex items-center gap-1 text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
              <Icon name="heart" size="sm" />{item.count}
            </span>
          </div>
        ))}
      </div>

      <DemoLabel><Icon name="check" size="sm" />Done</DemoLabel>
      <IntentCard intent={DEMO_DONE} />
      <p className="mt-2.5 px-1 font-serif text-sm italic leading-6" style={{ color: "var(--txt-m)" }}>
        &ldquo;{DEMO_DONE.done_note}&rdquo;
      </p>
    </div>
  );
}

function PublicLanding() {
  // Android is the only platform with a real artifact to download, so the link
  // stays hidden everywhere else. null means detection has not run yet.
  const platform = useInstallPlatform();

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

      <section id="top" className="pb-10 pt-14 text-center">
        <h1 className="font-serif text-[40px] font-medium leading-[1.08] tracking-[-.025em]">
          Save the things you want to do together.
        </h1>
        <p className="mx-auto mt-4 max-w-sm text-[15px] leading-7" style={{ color: "var(--txt-m)" }}>
          One shared list for the films, meals, and trips your people keep saying yes to. Hearts show what everyone wants. Done plans keep the memory.
        </p>
        <Link href="/login" className="btn-primary mx-auto mt-7 min-h-12 w-full max-w-xs px-6 text-sm">
          Create your first circle
        </Link>
        {platform === "android" && (
          <a href={APK_URL} className="mx-auto mt-4 flex w-fit items-center gap-1.5 py-1.5 text-xs font-medium"
            style={{ color: "var(--acc)" }}>
            <Icon name="download" size="sm" />
            Download for Android
          </a>
        )}
      </section>

      <section aria-label="A sample circle" className="pb-6">
        <p className="mb-2.5 text-center text-xs" style={{ color: "var(--txt-l)" }}>
          A sample circle, a few weeks in
        </p>
        <CirclePreview />
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

function HomeSkeleton() {
  return (
    <main className="py-5">
      <div className="mb-8 mt-16"><Skeleton height={96} count={3} /></div>
    </main>
  );
}

export default function Home() {
  const [ready, setReady] = useState(false);
  // A cached me() (client-side navigation back home) renders at once, before
  // the session check finishes.
  const [user, setUser] = useState<User | null>(() => getCached<{ user: User }>("me")?.user ?? null);
  const [circles, setCircles] = useState<Circle[] | null>(() => getCached<{ circles: Circle[] }>("me")?.circles ?? null);
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

  // No cache and no finished session check. The static HTML keeps the landing
  // page for visitors and crawlers; the inline script in layout.tsx swaps in
  // the skeleton when a session is stored, so signed-in users never see it.
  if (!ready && !user)
    return (
      <>
        <div className="gate-out"><PublicLanding /></div>
        <div className="gate-in"><HomeSkeleton /></div>
      </>
    );

  if (!user)
    return <PublicLanding />;

  if (!circles)
    return <HomeSkeleton />;

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
