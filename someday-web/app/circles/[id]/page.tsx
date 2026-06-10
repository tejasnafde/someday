"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Sprite";
import { EmptyState, IntentCard, MemberDot, NavBar, Spinner, memberColor } from "@/components/ui";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/useAuth";
import type { Category, CircleDetail, Intent } from "@/lib/types";

const TABS = ["All", "Shortlist", "Done"] as const;
const CATEGORIES: (Category | "All")[] = ["All", "watch", "eat", "visit", "read", "play", "trip"];

export default function CirclePage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [intents, setIntents] = useState<Intent[] | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("All");
  const [category, setCategory] = useState<Category | "All">("All");
  const [userId, setUserId] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState("");
  const nameRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    api.circle(id).then(setCircle);
    const params =
      tab === "Shortlist" ? { shortlist: true }
      : tab === "Done" ? { task_status: "done" }
      : category !== "All" ? { category }
      : undefined;
    api.intents(id, params).then(setIntents);
  }, [id, tab, category]);

  useEffect(() => {
    if (!ready) return;
    load();
    supabase.auth.getSession().then(({ data }) => setUserId(data.session?.user.id ?? ""));
  }, [ready, load]);

  useEffect(() => {
    if (renaming) nameRef.current?.focus();
  }, [renaming]);

  async function react(intentId: string) {
    await api.react(intentId);
    load();
  }

  async function boost(intentId: string) {
    await api.boost(intentId);
    load();
  }

  async function rename(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed && trimmed !== circle?.name) await api.updateCircle(id, { name: trimmed });
    setRenaming(false);
    load();
  }

  async function leave() {
    if (!confirm("Leave this circle?")) return;
    await api.leaveCircle(id);
    router.push("/");
  }

  async function remove() {
    if (!confirm("Delete this circle for everyone? This can't be undone.")) return;
    await api.deleteCircle(id);
    router.push("/");
  }

  if (!ready || !circle) return <Spinner />;

  const isOwner = userId === circle.owner_id;

  const visible = tab === "All" && category === "All"
    ? intents?.filter((i) => i.task_status !== "done" && i.task_status !== "archived")
    : intents;

  return (
    <main>
      <NavBar
        title={
          renaming ? (
            <form onSubmit={rename} className="flex items-center gap-1.5">
              <input
                ref={nameRef}
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Escape" && setRenaming(false)}
                className="min-w-0 flex-1 rounded-[var(--rs)] px-2.5 py-1 font-serif text-lg font-semibold outline-none"
                style={{ background: "var(--glass-lo)", border: "1px solid var(--acc)", color: "var(--txt)" }}
              />
              <button type="submit" aria-label="Save name"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white"
                style={{ background: "var(--acc)" }}>
                <Icon name="check" size="sm" />
              </button>
            </form>
          ) : (
            <span className="flex items-center gap-2">
              <span className="truncate">{circle.name}</span>
              {isOwner && (
                <button
                  onClick={() => { setName(circle.name); setRenaming(true); }}
                  aria-label="Rename circle"
                  className="shrink-0"
                  style={{ color: "var(--txt-l)" }}
                >
                  <Icon name="pencil" size="sm" />
                </button>
              )}
            </span>
          )
        }
        subtitle={`${circle.member_count} members · ${circle.open_intent_count} ideas`}
        back="/"
        right={
          <div className="flex items-center gap-2">
            <div className="flex">
              {circle.members.slice(0, 4).map((m, i) => (
                <MemberDot key={m.user_id} name={m.display_name} color={memberColor(i)} />
              ))}
            </div>
            <Link href={`/circles/${id}/invite`} aria-label="Invite"
              className="glass flex h-9 w-9 items-center justify-center rounded-full" style={{ color: "var(--txt-m)" }}>
              <Icon name="link" size="sm" />
            </Link>
          </div>
        }
      />

      <div className="flex border-b" style={{ borderColor: "var(--brd-s)" }}>
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className="-mb-px flex items-center gap-1.5 px-3.5 py-2.5 text-[13px] font-medium"
            style={{
              color: tab === t ? "var(--acc)" : "var(--txt-l)",
              borderBottom: `2px solid ${tab === t ? "var(--acc)" : "transparent"}`,
            }}>
            {t === "Shortlist" && <Icon name="star" size="sm" />}
            {t === "Done" && <Icon name="check" size="sm" />}
            {t}
          </button>
        ))}
      </div>

      {tab === "All" && (
        <div className="-mx-5 flex gap-2 overflow-x-auto px-5 py-3 [scrollbar-width:none]">
          {CATEGORIES.map((c) => (
            <button key={c} onClick={() => setCategory(c)}
              className="whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium capitalize"
              style={{
                background: category === c ? "var(--acc-l)" : "var(--glass-lo)",
                border: `1px solid ${category === c ? "var(--acc)44" : "var(--brd-s)"}`,
                color: category === c ? "var(--acc)" : "var(--txt-m)",
              }}>
              {c}
            </button>
          ))}
        </div>
      )}

      <div className="mt-2 flex flex-col gap-3">
        {!visible ? (
          <Spinner />
        ) : visible.length === 0 ? (
          <EmptyState
            message={
              tab === "Shortlist"
                ? "Nothing here yet — when two of you are interested in the same thing, it shows up here."
                : tab === "Done"
                  ? "No memories yet. Mark something done after you do it together."
                  : "Nothing saved yet — drop in the first thing you should do together."
            }
          />
        ) : (
          visible.map((i) => (
            <IntentCard key={i.id} intent={i} onReact={() => react(i.id)} onBoost={() => boost(i.id)} />
          ))
        )}
      </div>

      <div className="mt-6 flex flex-col gap-3">
        <Link href={`/circles/${id}/payoff`} className="btn-primary w-full py-4 text-sm">
          <Icon name="target" />
          What are we doing today?
        </Link>
        <Link href={`/circles/${id}/add`} className="btn-ghost w-full py-3.5 text-sm">
          <Icon name="plus" size="sm" />
          Add something
        </Link>
      </div>

      <div className="mb-8 mt-10 flex justify-center gap-6 text-xs font-medium" style={{ color: "var(--txt-l)" }}>
        <button onClick={leave} className="flex items-center gap-1.5">
          <Icon name="log-out" size="sm" />
          Leave circle
        </button>
        {isOwner && (
          <button onClick={remove} className="flex items-center gap-1.5" style={{ color: "var(--cp)" }}>
            <Icon name="trash" size="sm" />
            Delete circle
          </button>
        )}
      </div>
    </main>
  );
}
