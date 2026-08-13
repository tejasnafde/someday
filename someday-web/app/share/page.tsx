"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon } from "@/components/Sprite";
import { NavBar, Spinner, circleTheme } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { Circle } from "@/lib/types";

export default function SharedCapturePage() {
  return <Suspense fallback={<Spinner />}><SharedCapture /></Suspense>;
}

function SharedCapture() {
  const ready = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [circles, setCircles] = useState<Circle[] | null>(null);
  const [selected, setSelected] = useState("");
  const [title, setTitle] = useState(() => params.get("title") ?? "");
  const [url, setUrl] = useState(() => params.get("url") ?? "");

  useEffect(() => {
    if (!ready) return;
    api.me().then(({ circles: items }) => {
      setCircles(items);
      if (items.length === 1) setSelected(items[0].id);
    });
  }, [ready]);

  function continueCapture() {
    if (!selected || (!title.trim() && !url.trim())) return;
    const query = new URLSearchParams();
    if (title.trim()) query.set("title", title.trim());
    if (url.trim()) query.set("url", url.trim());
    router.push(`/circles/${selected}/add?${query}`);
  }

  if (!ready || !circles) return <Spinner />;

  return (
    <main>
      <NavBar title="Save shared idea" back="/" />

      <div className="glass rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--acc)" }}>
          <Icon name="link" size="sm" />
          Shared with Someday
        </div>
        <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="Paste the shared link"
          className="glass w-full rounded-[var(--rs)] px-3.5 py-3 text-sm outline-none" />
        <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What’s the plan?"
          className="glass mt-3 w-full rounded-[var(--rs)] px-3.5 py-3 font-serif text-sm outline-none" />
      </div>

      <h2 className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
        Choose a circle
      </h2>
      <div className="flex flex-col gap-2.5">
        {circles.length === 0 ? (
          <div className="glass rounded-[var(--r)] p-5 text-sm" style={{ color: "var(--txt-m)" }}>
            Create a circle first, then share the link again.
          </div>
        ) : circles.map((circle) => {
          const active = selected === circle.id;
          const theme = circleTheme(circle.id);
          return (
            <button key={circle.id} onClick={() => setSelected(circle.id)}
              className="glass flex min-h-12 items-center gap-3 rounded-[var(--r)] px-4 py-3 text-left transition-transform active:scale-[.96]"
              style={{ borderColor: active ? "var(--acc)" : "var(--brd)", color: "var(--txt)" }}>
              <span className="flex h-8 w-8 items-center justify-center rounded-[var(--rs)]"
                style={{ background: `var(--${theme.key}-l)`, color: `var(--${theme.key})` }}>
                <Icon name={theme.icon} size="sm" />
              </span>
              <span className="min-w-0 flex-1 truncate font-serif text-sm font-semibold">{circle.name}</span>
              {active && <span style={{ color: "var(--acc)" }}><Icon name="check" size="sm" /></span>}
            </button>
          );
        })}
      </div>

      <button onClick={continueCapture} disabled={!selected || (!title.trim() && !url.trim())}
        className="btn-primary mt-5 w-full py-3.5 text-sm disabled:opacity-50">
        Continue
      </button>
    </main>
  );
}
