"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Sprite";
import { Tour } from "@/components/Tour";
import { CircleAvatar, EmptyState, IntentCard, MemberDot, NavBar, Skeleton, Spinner, circleTheme, memberColor } from "@/components/ui";
import { api } from "@/lib/api";
import { resizeImage } from "@/lib/image";
import { getCached, setCached } from "@/lib/cache";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/useAuth";
import type { Category, CircleDetail, Intent } from "@/lib/types";

const TABS = ["All", "Shortlist", "Done"] as const;
const CATEGORIES: (Category | "All")[] = ["All", "watch", "eat", "visit", "read", "play", "trip", "talk"];

export default function CirclePage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [intents, setIntents] = useState<Intent[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]>("All");
  const [category, setCategory] = useState<Category | "All">("All");
  const [tag, setTag] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [userId, setUserId] = useState("");
  const [intentsError, setIntentsError] = useState<string | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [photoV, setPhotoV] = useState(0);
  const [copied, setCopied] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);

  const intentsKey = `intents:${id}:${tab}:${category}:${tag ?? ""}`;

  const load = useCallback(() => {
    const cachedCircle = getCached<CircleDetail>(`circle:${id}`);
    if (cachedCircle) setCircle(cachedCircle);
    api.circle(id).then((c) => {
      setCached(`circle:${id}`, c);
      setCircle(c);
    }).catch(() => router.replace("/"));

    const cachedIntents = getCached<{ items: Intent[]; next_cursor: string | null }>(intentsKey);
    if (cachedIntents) { setIntents(cachedIntents.items); setNextCursor(cachedIntents.next_cursor); }
    const params: Parameters<typeof api.intents>[1] =
      tab === "Shortlist" ? { shortlist: true }
      : tab === "Done" ? { task_status: "done" }
      : {};
    if (tab === "All") {
      if (category !== "All") params!.category = category;
      if (tag) params!.tag = tag;
    }
    api.intents(id, params).then((res) => {
      // Tolerate a bare-array response (older API shape): degrade to empty, never stick.
      const items = Array.isArray(res) ? res : (res?.items ?? []);
      const next_cursor = Array.isArray(res) ? null : (res?.next_cursor ?? null);
      setCached(intentsKey, { items, next_cursor });
      setIntents(items);
      setNextCursor(next_cursor);
      setIntentsError(null);
    }).catch((e) => {
      setIntents([]);
      setNextCursor(null);
      setIntentsError(e?.message ?? "Could not load");
    });
  }, [id, tab, category, tag, intentsKey, router]);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    const params: Parameters<typeof api.intents>[1] =
      tab === "Shortlist" ? { shortlist: true }
      : tab === "Done" ? { task_status: "done" }
      : {};
    if (tab === "All") {
      if (category !== "All") params!.category = category;
      if (tag) params!.tag = tag;
    }
    try {
      const { items, next_cursor } = await api.intents(id, { ...params, cursor: nextCursor });
      setIntents((prev) => {
        const all = [...(prev ?? []), ...items];
        setCached(intentsKey, { items: all, next_cursor });
        return all;
      });
      setNextCursor(next_cursor);
    } catch {
      // leave existing list intact; user can retry
    } finally {
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    if (!ready) return;
    load();
    supabase.auth.getSession().then(({ data }) => setUserId(data.session?.user.id ?? ""));
  }, [ready, load]);

  useEffect(() => {
    if (!ready) return;
    api.circleTags(id).then(setTags).catch(() => {});
  }, [ready, id]);

  async function retryPreview(intentId: string) {
    const updated = await api.refreshPreview(intentId);
    patchIntent(intentId, (i) => ({ ...i, link_meta: updated.link_meta }));
  }

  useEffect(() => {
    if (renaming) nameRef.current?.focus();
  }, [renaming]);

  function patchIntent(intentId: string, patch: (i: Intent) => Intent) {
    setIntents((prev) => {
      const next = prev?.map((i) => (i.id === intentId ? patch(i) : i)) ?? prev;
      if (next) setCached(intentsKey, { items: next, next_cursor: nextCursor });
      return next;
    });
  }

  function react(intentId: string) {
    patchIntent(intentId, (i) => ({
      ...i,
      reacted_by_me: !i.reacted_by_me,
      reaction_count: i.reaction_count + (i.reacted_by_me ? -1 : 1),
    }));
    api.react(intentId).catch(() => load());
  }

  function boost(intentId: string) {
    patchIntent(intentId, (i) => ({ ...i, boosted_by_me: !i.boosted_by_me }));
    api.boost(intentId).catch(() => load());
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

  async function copyInvite() {
    await navigator.clipboard.writeText(`${location.origin}/join/${circle!.invite_token}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
              <CircleAvatar key={photoV} circleId={id} themeKey={circleTheme(id).key} icon={circleTheme(id).icon} size={30} v={photoV || undefined} />
              <span className="truncate">{circle.name}</span>
              {isOwner && (
                <>
                  <button
                    onClick={() => { setName(circle.name); setRenaming(true); }}
                    aria-label="Rename circle"
                    className="shrink-0"
                    style={{ color: "var(--txt-l)" }}
                  >
                    <Icon name="pencil" size="sm" />
                  </button>
                  <label aria-label="Circle photo" className="shrink-0 cursor-pointer" style={{ color: "var(--txt-l)" }}>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={async (e) => {
                        const f = e.target.files?.[0];
                        if (!f) return;
                        const blob = await resizeImage(f);
                        await api.uploadCirclePhoto(id, blob);
                        setPhotoV(Date.now());
                      }}
                    />
                    <Icon name="film" size="sm" />
                  </label>
                </>
              )}
            </span>
          )
        }
        subtitle={`${circle.member_count} members · ${circle.open_intent_count} ideas`}
        back="/"
        right={
          <div className="flex items-center gap-2">
            <div className="flex">
              <Link href={`/circles/${id}/members`} aria-label="See members" className="flex">
                {circle.members.slice(0, 4).map((m, i) => (
                  <MemberDot key={m.user_id} name={m.display_name} color={memberColor(i)} src={m.avatar_url} />
                ))}
              </Link>
            </div>
            <button onClick={() => setInviteOpen(true)} aria-label="Invite" data-tour="invite"
              className="glass flex h-9 w-9 items-center justify-center rounded-full" style={{ color: "var(--txt-m)" }}>
              <Icon name="link" size="sm" />
            </button>
          </div>
        }
      />

      <div data-tour="status-tabs" className="flex border-b" style={{ borderColor: "var(--brd-s)" }}>
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
        <>
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
          {tags.length > 0 && (
            <div data-tour="tag-filter" className="-mx-5 flex items-center gap-2 overflow-x-auto px-5 pb-2 [scrollbar-width:none]">
              <span className="shrink-0" style={{ color: "var(--txt-l)" }}>
                <Icon name="settings" size="sm" />
              </span>
              {tags.map((tg) => (
                <button key={tg} onClick={() => setTag(tag === tg ? null : tg)}
                  className="flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-3 py-1 text-[11px] font-semibold"
                  style={{
                    background: tag === tg ? "var(--cp-l)" : "var(--glass-lo)",
                    border: `1px solid ${tag === tg ? "var(--cp)44" : "var(--brd-s)"}`,
                    color: tag === tg ? "var(--cp)" : "var(--txt-m)",
                  }}>
                  {tg}
                  {tag === tg && <Icon name="x" size="sm" />}
                </button>
              ))}
            </div>
          )}
        </>
      )}

      <div className="mt-2 flex flex-col gap-3">
        {!visible ? (
          <Skeleton height={180} count={3} />
        ) : intentsError ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <p className="text-sm" style={{ color: "var(--cp)" }}>{intentsError}</p>
            <button onClick={load} className="btn-ghost px-5 py-2 text-sm">Retry</button>
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            message={
              tab === "Shortlist"
                ? "Nothing here yet - when two of you are interested in the same thing, it shows up here."
                : tab === "Done"
                  ? "No memories yet. Mark something done after you do it together."
                  : "Nothing saved yet - drop in the first thing you should do together."
            }
          />
        ) : (
          visible.map((i, idx) => (
            <div key={i.id} data-tour={idx === 0 ? "intent-card" : undefined}>
              <IntentCard intent={i} onReact={() => react(i.id)} onBoost={() => boost(i.id)} onRetryPreview={retryPreview} />
            </div>
          ))
        )}
      </div>

      {nextCursor && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="btn-ghost px-6 py-2.5 text-sm disabled:opacity-60"
          >
            {loadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      )}

      <div className="fixed inset-x-0 bottom-0 z-30">
        <div className="mx-auto flex max-w-md items-center gap-2.5 px-5 pb-5 pt-4"
          style={{ background: "linear-gradient(to top, var(--bg-a) 55%, transparent)" }}>
          <Link href={`/circles/${id}/payoff`} data-tour="payoff" className="btn-primary flex-1 py-4 text-sm">
            <Icon name="target" />
            What are we doing today?
          </Link>
          <Link href={`/circles/${id}/add`} data-tour="add-intent" aria-label="Add something"
            className="glass-hi flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-full"
            style={{ color: "var(--acc)", boxShadow: "var(--shc)" }}>
            <Icon name="plus" size="lg" />
          </Link>
        </div>
      </div>
      <div className="h-20" />

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

      {inviteOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
          style={{ background: "rgba(0,0,0,.4)" }}
          onClick={() => setInviteOpen(false)}
        >
          <div
            className="glass-hi mx-5 mb-8 w-full max-w-sm rounded-[var(--r)] p-5 sm:mb-0"
            style={{ boxShadow: "var(--shc)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="font-serif text-lg font-semibold">Invite to {circle.name}</div>
                <div className="mt-0.5 text-xs" style={{ color: "var(--txt-m)" }}>
                  Anyone with this link can join.
                </div>
              </div>
              <button onClick={() => setInviteOpen(false)} aria-label="Close"
                className="glass flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
                style={{ color: "var(--txt-m)" }}>
                <Icon name="x" size="sm" />
              </button>
            </div>
            <div className="mt-4 break-all rounded-[var(--rs)] px-3 py-2.5 text-xs"
              style={{ background: "var(--glass-lo)", color: "var(--txt-m)", border: "1px solid var(--brd-s)" }}>
              {`${typeof location !== "undefined" ? location.origin : ""}/join/${circle.invite_token}`}
            </div>
            <button onClick={copyInvite} className="btn-primary mt-3 w-full py-3 text-sm">
              <Icon name={copied ? "check" : "copy"} size="sm" />
              {copied ? "Copied" : "Copy link"}
            </button>
          </div>
        </div>
      )}

      {intents && <Tour page="circle" />}
    </main>
  );
}
