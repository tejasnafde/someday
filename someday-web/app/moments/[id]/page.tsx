"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Sprite";
import { MemberDot, NavBar, Spinner, memberColor } from "@/components/ui";
import { api } from "@/lib/api";
import { resizeImage } from "@/lib/image";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/useAuth";
import type { CircleDetail, Moment, MomentPost } from "@/lib/types";

function cityOf(tz: string): string {
  return (tz.split("/").pop() ?? tz).replace(/_/g, " ");
}

function localClock(createdAt: string, tz: string): string {
  try {
    const d = new Date(createdAt.replace(" ", "T"));
    return d.toLocaleTimeString([], { timeZone: tz, hour: "numeric", minute: "2-digit" });
  } catch {
    return "";
  }
}

export default function MomentPage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const [moment, setMoment] = useState<Moment | null>(null);
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [userId, setUserId] = useState("");
  const [caption, setCaption] = useState("");
  const [pending, setPending] = useState<Blob | null>(null);
  const [pendingUrl, setPendingUrl] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");
  const [savedTitle, setSavedTitle] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  const load = useCallback(() => {
    api.moment(id).then((m) => {
      setMoment(m);
      api.circle(m.circle_id).then(setCircle).catch(() => {});
    }).catch((e) => setError(e instanceof Error ? e.message : "Could not load"));
  }, [id]);

  useEffect(() => {
    if (!ready) return;
    load();
    supabase.auth.getSession().then(({ data }) => setUserId(data.session?.user.id ?? ""));
  }, [ready, load]);

  async function pickPhoto(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const blob = await resizeImage(f);
    setPending(blob);
    setPendingUrl(URL.createObjectURL(blob));
  }

  async function post() {
    if (!pending || posting) return;
    setPosting(true);
    setError("");
    try {
      const updated = await api.postMoment(id, pending, caption);
      setMoment(updated);
      setPending(null);
      setPendingUrl(null);
      setCaption("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not post");
    } finally {
      setPosting(false);
    }
  }

  async function somedayTogether(p: MomentPost) {
    if (savedIds.has(p.id)) return;
    try {
      const intent = await api.somedayFromPost(p.id);
      setSavedIds((prev) => new Set(prev).add(p.id));
      setSavedTitle(intent.title);
      if (toastTimer.current) clearTimeout(toastTimer.current);
      toastTimer.current = setTimeout(() => setSavedTitle(null), 2600);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    }
  }

  if (!ready || (!moment && !error)) return <Spinner />;
  if (!moment) {
    return (
      <main>
        <NavBar title="Meanwhile" back="/" />
        <p className="py-10 text-center text-sm" style={{ color: "var(--cp)" }}>{error}</p>
      </main>
    );
  }

  const posts = moment.posts;
  const postedIds = new Set(posts.map((p) => String(p.user_id)));
  const absent = (circle?.members ?? []).filter((m) => !postedIds.has(String(m.user_id)));
  const cities = [...new Set(posts.map((p) => cityOf(p.tz)))];
  const dateLabel = new Date(moment.moment_date + "T00:00:00").toLocaleDateString([], {
    weekday: "short", day: "numeric", month: "short",
  });

  return (
    <main>
      <NavBar title={moment.circle_name ?? "Meanwhile"} back={`/circles/${moment.circle_id}`} />

      <div className="py-3 text-center">
        <h1 className="font-serif text-[24px] font-medium leading-tight">
          Meanwhile{cities.length > 0 && <>, in <em style={{ color: "var(--acc)" }}>{cities.length === 1 ? cities[0] : `${cities.length} cities`}</em></>}
        </h1>
        <p className="mt-1 text-xs" style={{ color: "var(--txt-m)" }}>{dateLabel}</p>
        {!moment.revealed && !moment.my_post && (
          <p className="mt-1 text-[11px]" style={{ color: "var(--txt-l)" }}>
            Post yours to see everyone - or wait for midnight.
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* my tile: capture or my post */}
        {!moment.my_post ? (
          <div className="flex flex-col overflow-hidden" style={{ borderRadius: "var(--rs)", border: "1px dashed var(--brd-h)", background: "var(--glass-lo)", aspectRatio: "3/4" }}>
            {pendingUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={pendingUrl} alt="" className="h-full w-full object-cover" />
            ) : (
              <button onClick={() => fileRef.current?.click()}
                className="flex h-full w-full flex-col items-center justify-center gap-2 text-[11px] font-semibold"
                style={{ color: "var(--txt-m)" }}>
                <Icon name="camera" size="lg" />
                Tap to capture
                <span className="font-normal" style={{ color: "var(--txt-l)" }}>what are you doing right now?</span>
              </button>
            )}
            <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={pickPhoto} />
          </div>
        ) : (
          <MomentTile post={moment.my_post} mine />
        )}

        {posts.filter((p) => String(p.user_id) !== String(userId)).map((p) =>
          p.photo_url ? (
            <MomentTile key={p.id} post={p}
              saved={savedIds.has(p.id)}
              onSomeday={() => somedayTogether(p)} />
          ) : (
            <div key={p.id} className="flex flex-col items-center justify-center gap-2"
              style={{ borderRadius: "var(--rs)", border: "1px solid var(--brd-s)", background: "var(--glass)", aspectRatio: "3/4" }}>
              <span className="glass-hi flex h-9 w-9 items-center justify-center rounded-full" style={{ color: "var(--acc)", boxShadow: "var(--shc)" }}>
                <Icon name="check" size="sm" />
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                {p.display_name ?? "Someone"} posted
              </span>
              <span className="text-[10px]" style={{ color: "var(--txt-l)" }}>
                {cityOf(p.tz)}{p.late ? " · late" : ""}
              </span>
            </div>
          ),
        )}

        {absent.map((m, i) => (
          <div key={m.user_id} className="flex flex-col items-center justify-center gap-2"
            style={{ borderRadius: "var(--rs)", border: "1px dashed var(--brd-s)", background: "var(--glass-lo)", aspectRatio: "3/4" }}>
            <MemberDot name={m.display_name} color={memberColor(i)} src={m.avatar_url} />
            <span className="text-[10px]" style={{ color: "var(--txt-l)" }}>
              {(m.display_name ?? "Someone").split(" ")[0]} - not yet
            </span>
          </div>
        ))}
      </div>

      {!moment.my_post && pending && (
        <div className="mt-4 flex flex-col gap-2.5">
          <input value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={140}
            placeholder="One line about it (optional)"
            className="glass w-full rounded-[var(--rs)] px-3.5 py-3 text-sm outline-none" />
          <div className="flex gap-2.5">
            <button onClick={post} disabled={posting} className="btn-primary flex-1 py-3 text-sm disabled:opacity-60">
              <Icon name="camera" size="sm" />
              {posting ? "Posting…" : "Post"}
            </button>
            <button onClick={() => { setPending(null); setPendingUrl(null); }} className="btn-ghost px-5 py-3 text-sm">
              Retake
            </button>
          </div>
        </div>
      )}

      {error && moment && <p className="mt-3 text-center text-xs" style={{ color: "var(--cp)" }}>{error}</p>}

      {savedTitle && (
        <div className="glass-hi fixed inset-x-5 bottom-6 z-40 mx-auto flex max-w-sm items-center gap-2 rounded-[var(--rs)] px-3.5 py-3 text-xs" style={{ boxShadow: "var(--shc)" }}>
          <span style={{ color: "var(--sp-t)" }}><Icon name="check" size="sm" /></span>
          Saved to the list: &ldquo;{savedTitle}&rdquo;
        </div>
      )}
    </main>
  );
}

function MomentTile({ post, mine, saved, onSomeday }: {
  post: MomentPost;
  mine?: boolean;
  saved?: boolean;
  onSomeday?: () => void;
}) {
  return (
    <div className="relative overflow-hidden" style={{ borderRadius: "var(--rs)", aspectRatio: "3/4", outline: "1px solid var(--img-outline)", outlineOffset: -1 }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={post.photo_url!} alt="" className="absolute inset-0 h-full w-full object-cover" />
      {post.caption && (
        <span className="absolute left-2 right-2 top-2 w-fit max-w-[92%] rounded-lg px-2 py-1 text-[10px] text-white"
          style={{ background: "rgba(10,8,16,.5)", backdropFilter: "blur(6px)" }}>
          {post.caption}
        </span>
      )}
      {!mine && onSomeday && (
        <button onClick={onSomeday}
          className="absolute bottom-9 right-2 z-10 flex items-center gap-1 rounded-full px-2.5 py-1.5 text-[9.5px] font-bold text-white transition-transform active:scale-[.96]"
          style={{ background: saved ? "linear-gradient(135deg, var(--acc), var(--acc-m))" : "rgba(10,8,16,.55)", backdropFilter: "blur(8px)" }}>
          <Icon name={saved ? "check" : "plus"} size="sm" />
          {saved ? "on the list" : "someday, together"}
        </button>
      )}
      <div className="absolute inset-x-0 bottom-0 px-2.5 pb-2 pt-6 text-white" style={{ background: "linear-gradient(transparent, rgba(10,8,16,.72))" }}>
        <div className="text-[11px] font-bold">{mine ? "You" : post.display_name ?? "Someone"}</div>
        <div className="flex items-center gap-1 text-[9.5px] opacity-85">
          <Icon name="map-pin" size="sm" />
          {cityOf(post.tz)} · {localClock(post.created_at, post.tz)}{post.late ? " · late" : ""}
        </div>
      </div>
    </div>
  );
}
