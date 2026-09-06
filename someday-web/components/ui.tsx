"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "./Sprite";
import type { Intent, TaskStatus } from "@/lib/types";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.getAttribute("data-theme") === "dark");
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className="glass flex h-9 w-9 items-center justify-center rounded-full"
      style={{ color: "var(--txt-m)" }}
    >
      <Icon name={dark ? "sun" : "moon"} size="sm" />
    </button>
  );
}

const CIRCLE_THEMES = [
  { key: "cp", icon: "eye" },
  { key: "cg", icon: "users" },
  { key: "cb", icon: "globe" },
];

export function circleTheme(id: string) {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) | 0;
  return CIRCLE_THEMES[Math.abs(h) % CIRCLE_THEMES.length];
}

const DOT_COLORS = ["var(--cp)", "var(--acc)", "var(--cg)", "var(--cb)", "#E6920A", "#E04444"];

export function memberColor(index: number) {
  return DOT_COLORS[index % DOT_COLORS.length];
}

export function MemberDot({ name, color, size = 22, src }: { name: string | null; color: string; size?: number; src?: string | null }) {
  return (
    <div
      className="-mr-1 flex items-center justify-center overflow-hidden rounded-full font-bold text-white"
      style={{
        width: size,
        height: size,
        background: color,
        border: "2px solid var(--brd)",
        fontSize: size * 0.4,
        boxShadow: "0 1px 4px rgba(0,0,0,.14)",
      }}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt="" className="h-full w-full object-cover" />
      ) : name ? (
        name.charAt(0).toUpperCase()
      ) : (
        ""
      )}
    </div>
  );
}

export function CircleAvatar({ circleId, themeKey, icon, size = 48, v }: { circleId: string; themeKey: string; icon: string; size?: number; v?: number }) {
  const [failed, setFailed] = useState(false);
  if (failed)
    return (
      <div className="flex shrink-0 items-center justify-center rounded-2xl"
        style={{ width: size, height: size, background: `var(--${themeKey}-l)`, color: `var(--${themeKey})`, border: "1px solid var(--brd)" }}>
        <Icon name={icon} size="lg" />
      </div>
    );
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/circle-photos/${circleId}${v ? `?v=${v}` : ""}`}
      alt=""
      onError={() => setFailed(true)}
      className="shrink-0 rounded-2xl object-cover"
      style={{ width: size, height: size, border: "1px solid var(--brd)" }}
    />
  );
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  saved: { bg: "var(--ss)", text: "var(--ss-t)" },
  interested: { bg: "var(--si)", text: "var(--si-t)" },
  planned: { bg: "var(--sp)", text: "var(--sp-t)" },
  done: { bg: "var(--sp)", text: "var(--sp-t)" },
  archived: { bg: "var(--ss)", text: "var(--ss-t)" },
};

export function StatusBadge({ status }: { status: TaskStatus }) {
  const s = STATUS_STYLES[status];
  return (
    <span
      className="rounded-full px-2.5 py-1 text-[10px] font-semibold capitalize"
      style={{ background: s.bg, color: s.text, border: `1.5px solid ${s.text}33` }}
    >
      {status}
    </span>
  );
}

export const CATEGORY_ICONS: Record<string, string> = {
  watch: "film",
  eat: "utensils",
  visit: "map-pin",
  read: "book-open",
  play: "gamepad",
  trip: "plane",
  talk: "message-circle",
  other: "star",
};

const CATEGORY_GRADIENTS: Record<string, string> = {
  watch: "linear-gradient(135deg,#1a1a2e,#3d2c8d)",
  eat: "linear-gradient(135deg,#2c1810,#7a3010)",
  visit: "linear-gradient(135deg,#0a1a2c,#1a3a6b)",
  read: "linear-gradient(135deg,#0a2c18,#1a6b3a)",
  play: "linear-gradient(135deg,#2c0a2c,#6b1a5a)",
  trip: "linear-gradient(135deg,#0a2c2c,#1a5a6b)",
  talk: "linear-gradient(135deg,#2c0a1a,#6b1a3a)",
  other: "linear-gradient(135deg,#1c1c1c,#3a3a3a)",
};

export function IntentPreview({ intent, height = 106 }: { intent: Pick<Intent, "category" | "link_meta">; height?: number }) {
  const image = intent.link_meta?.image;
  if (image) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={image} alt="" className="img-edge w-full object-cover" style={{ height }} />;
  }
  return (
    <div
      className="flex w-full items-center justify-center"
      style={{ height, background: CATEGORY_GRADIENTS[intent.category ?? "other"], color: "rgba(255,255,255,.3)" }}
    >
      <Icon name={CATEGORY_ICONS[intent.category ?? "other"]} size="xl" />
    </div>
  );
}

function RetryPreviewBanner({ intentId, onRetry }: { intentId: string; onRetry: (id: string) => Promise<void> | void }) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState(false);
  async function retry(e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation();
    setBusy(true); setErr(false);
    try { await onRetry(intentId); setDone(true); } catch { setErr(true); }
    finally { setBusy(false); }
  }
  if (done) return null;
  return (
    <div className="mt-2.5 flex items-center gap-2 rounded-[var(--rs)] px-2.5 py-2"
      style={{ background: "var(--cp-l)", border: "1px dashed var(--cp)44" }}>
      <span style={{ color: "var(--cp)" }}><Icon name="x" size="sm" /></span>
      <span className="flex-1 text-[11px]" style={{ color: "var(--cp)" }}>
        {err ? "Still couldn't load a preview." : "No preview when this was saved."}
      </span>
      <button onClick={retry} disabled={busy}
        className="rounded-md px-2 py-1 text-[11px] font-bold disabled:opacity-50"
        style={{ background: "var(--glass)", color: "var(--cp)", border: "1px solid var(--cp)44" }}>
        {busy ? "Loading…" : "Retry"}
      </button>
    </div>
  );
}

export function IntentCard({ intent, onReact, onBoost, onRetryPreview, onTagClick }: {
  intent: Intent;
  onReact?: () => void;
  onBoost?: () => void;
  onRetryPreview?: (id: string) => Promise<void> | void;
  onTagClick?: (tag: string) => void;
}) {
  const previewMissing = !!intent.url && !intent.link_meta?.title;
  const detailHref = `/intents/${intent.id}`;
  const autoTags = intent.auto_tags ?? [];
  // Two-zone card: the preview and title open the saved link directly (the
  // whole point of saving it); the bottom strip goes to the detail page.
  // Cards without a URL keep the old behavior everywhere.
  const openZone = (children: React.ReactNode, block = false) =>
    intent.url ? (
      <a href={intent.url} target="_blank" rel="noreferrer" className={`group relative ${block ? "block" : ""}`}>
        {children}
      </a>
    ) : (
      <Link href={detailHref} className={block ? "block" : ""}>{children}</Link>
    );
  return (
    <div className="overflow-hidden" style={{ borderRadius: "var(--r)", boxShadow: "var(--shc)" }}>
      {openZone(
        <>
          <IntentPreview intent={intent} />
          {intent.url && (
            <span
              className="absolute right-2.5 top-2.5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
              style={{ background: "rgba(12,10,20,.55)", backdropFilter: "blur(8px)" }}
            >
              <Icon name="link" size="sm" />
              Open
            </span>
          )}
        </>,
        true,
      )}
      <div className="glass-hi p-3.5" style={{ border: "none" }}>
        {openZone(
          <>
            {intent.link_meta?.site && (
              <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
                {intent.link_meta.site}
                {intent.url && <Icon name="link" size="sm" />}
              </div>
            )}
            <div className="font-serif text-sm font-semibold leading-snug">{intent.title}</div>
          </>,
        )}
        {intent.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {intent.tags.slice(0, 3).map((t) => {
              const suggested = autoTags.includes(t);
              return (
                <button
                  key={t}
                  onClick={() => onTagClick?.(t)}
                  title={suggested ? "Added automatically" : undefined}
                  className="rounded-full px-2.5 py-0.5 text-[10px] font-semibold"
                  style={{
                    background: suggested ? "transparent" : "var(--acc-l)",
                    color: "var(--acc)",
                    border: suggested ? "1px dashed var(--acc)77" : "1px solid var(--acc)2e",
                  }}
                >
                  {t}
                </button>
              );
            })}
            {intent.tags.length > 3 && (
              <span className="tnum rounded-full px-2 py-0.5 text-[10px] font-semibold"
                style={{ background: "var(--glass-lo)", color: "var(--txt-m)" }}>
                +{intent.tags.length - 3}
              </span>
            )}
          </div>
        )}
        {previewMissing && onRetryPreview && (
          <RetryPreviewBanner intentId={intent.id} onRetry={onRetryPreview} />
        )}
        <div className="mt-2.5 flex items-center justify-between gap-2">
          <Link
            href={detailHref}
            className="-m-1.5 flex flex-1 flex-wrap items-center gap-1.5 rounded-[var(--rs)] p-1.5"
            aria-label="View details"
          >
            <StatusBadge status={intent.task_status} />
            {intent.planned_for && (
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                style={{ background: "var(--sp)", color: "var(--sp-t)", border: "1px solid var(--sp-t)33" }}>
                <Icon name="clock" size="sm" />
                {intent.planned_for.length > 18 ? intent.planned_for.slice(0, 18) + "…" : intent.planned_for}
              </span>
            )}
            <span style={{ color: "var(--txt-l)" }}>
              <Icon name="chevron-right" size="sm" />
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <button
              onClick={onReact}
              aria-label="Toggle interested"
              className="tnum flex h-11 min-w-11 items-center justify-center gap-1 rounded-full px-3 text-xs font-semibold transition-transform active:scale-[.96]"
              style={{
                background: intent.reacted_by_me ? "var(--cp-l)" : "var(--glass-lo)",
                color: intent.reacted_by_me ? "var(--cp)" : "var(--txt-m)",
                border: `1px solid ${intent.reacted_by_me ? "var(--cp)44" : "var(--brd-s)"}`,
              }}
            >
              <Icon name="heart" size="sm" />
              {intent.reaction_count > 0 && intent.reaction_count}
            </button>
            <button
              onClick={onBoost}
              aria-label="Toggle boost"
              className="flex h-11 w-11 items-center justify-center rounded-full transition-transform active:scale-[.96]"
              style={{
                background: intent.boosted_by_me ? "rgba(234,165,0,.2)" : "rgba(234,165,0,.08)",
                border: `1.5px solid rgba(234,165,0,${intent.boosted_by_me ? ".5" : ".22"})`,
                color: "rgba(180,120,0,.9)",
              }}
            >
              <Icon name="zap" size="sm" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function NavBar({ title, subtitle, back, right }: { title: React.ReactNode; subtitle?: string; back?: string; right?: React.ReactNode }) {
  return (
    <div className="sticky top-0 z-20 -mx-5 mb-4 flex items-center gap-3 px-5 py-3"
      style={{ background: "var(--glass-nav)", backdropFilter: "var(--blur)", WebkitBackdropFilter: "var(--blur)", borderBottom: "1px solid var(--brd-s)" }}>
      {back && (
        <Link href={back} aria-label="Back"
          className="glass flex h-9 w-9 items-center justify-center rounded-full" style={{ color: "var(--txt-m)" }}>
          <Icon name="arrow-left" />
        </Link>
      )}
      <div className="min-w-0 flex-1">
        <div className="truncate font-serif text-lg font-semibold">{title}</div>
        {subtitle && <div className="tnum text-[11px]" style={{ color: "var(--txt-l)" }}>{subtitle}</div>}
      </div>
      {right}
    </div>
  );
}

export function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="h-7 w-7 animate-spin rounded-full border-2 border-transparent" style={{ borderTopColor: "var(--acc)", borderRightColor: "var(--acc)" }} />
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="glass rounded-[var(--r)] px-6 py-12 text-center text-sm" style={{ color: "var(--txt-m)" }}>
      {message}
    </div>
  );
}

export function Skeleton({ height = 80, count = 3 }: { height?: number; count?: number }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass animate-pulse rounded-[var(--r)]" style={{ height, opacity: 1 - i * 0.25 }} />
      ))}
    </div>
  );
}
