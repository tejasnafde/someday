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

const DOT_COLORS = ["var(--cp)", "var(--acc)", "var(--cg)", "var(--cb)", "#E6920A", "#E04444"];

export function memberColor(index: number) {
  return DOT_COLORS[index % DOT_COLORS.length];
}

export function MemberDot({ name, color, size = 22 }: { name: string | null; color: string; size?: number }) {
  return (
    <div
      className="-mr-1 flex items-center justify-center rounded-full font-bold text-white"
      style={{
        width: size,
        height: size,
        background: color,
        border: "2px solid var(--brd)",
        fontSize: size * 0.4,
        boxShadow: "0 1px 4px rgba(0,0,0,.14)",
      }}
    >
      {name ? name.charAt(0).toUpperCase() : ""}
    </div>
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
  other: "star",
};

const CATEGORY_GRADIENTS: Record<string, string> = {
  watch: "linear-gradient(135deg,#1a1a2e,#3d2c8d)",
  eat: "linear-gradient(135deg,#2c1810,#7a3010)",
  visit: "linear-gradient(135deg,#0a1a2c,#1a3a6b)",
  read: "linear-gradient(135deg,#0a2c18,#1a6b3a)",
  play: "linear-gradient(135deg,#2c0a2c,#6b1a5a)",
  trip: "linear-gradient(135deg,#0a2c2c,#1a5a6b)",
  other: "linear-gradient(135deg,#1c1c1c,#3a3a3a)",
};

export function IntentPreview({ intent, height = 106 }: { intent: Pick<Intent, "category" | "link_meta">; height?: number }) {
  const image = intent.link_meta?.image;
  if (image) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={image} alt="" className="w-full object-cover" style={{ height }} />;
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

export function IntentCard({ intent, onReact, onBoost }: { intent: Intent; onReact?: () => void; onBoost?: () => void }) {
  return (
    <div className="overflow-hidden" style={{ borderRadius: "var(--r)", boxShadow: "var(--shc)" }}>
      <Link href={`/intents/${intent.id}`}>
        <IntentPreview intent={intent} />
      </Link>
      <div className="glass-hi p-3.5" style={{ border: "none" }}>
        <Link href={`/intents/${intent.id}`}>
          {intent.link_meta?.site && (
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
              {intent.link_meta.site}
            </div>
          )}
          <div className="font-serif text-sm font-semibold leading-snug">{intent.title}</div>
        </Link>
        <div className="mt-2.5 flex items-center justify-between">
          <StatusBadge status={intent.task_status} />
          <div className="flex items-center gap-2">
            <button
              onClick={onReact}
              aria-label="Toggle interested"
              className="flex h-8 items-center gap-1 rounded-full px-2.5 text-xs font-semibold"
              style={{
                background: intent.reaction_count > 0 ? "var(--cp-l)" : "var(--glass-lo)",
                color: intent.reaction_count > 0 ? "var(--cp)" : "var(--txt-m)",
                border: "1px solid var(--brd-s)",
              }}
            >
              <Icon name="heart" size="sm" />
              {intent.reaction_count > 0 && intent.reaction_count}
            </button>
            <button
              onClick={onBoost}
              aria-label="Toggle boost"
              className="flex h-8 w-8 items-center justify-center rounded-full"
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
        {subtitle && <div className="text-[11px]" style={{ color: "var(--txt-l)" }}>{subtitle}</div>}
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
