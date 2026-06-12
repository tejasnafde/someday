"use client";

// Spotlight coachmark tour. Render <Tour page="..."/> once a page's data has
// loaded; it computes unseen steps for that page from the registry and the
// user's server-side tour_state, and runs a single coachmark pass.

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { getCached, setCached } from "@/lib/cache";
import { TOUR_REGISTRY, type TourPage, type TourStep } from "@/lib/tour/registry";
import type { Circle, User } from "@/lib/types";

const PENDING_KEY = "tour:pending";

function getPending(): string[] {
  try {
    return JSON.parse(localStorage.getItem(PENDING_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function setPending(ids: string[]) {
  if (ids.length === 0) localStorage.removeItem(PENDING_KEY);
  else localStorage.setItem(PENDING_KEY, JSON.stringify(ids));
}

/** Merge ids into the cached me() payload so other pages see them immediately. */
function mergeIntoCache(ids: string[]) {
  const me = getCached<{ user: User; circles: Circle[] }>("me");
  if (!me?.user) return;
  const seen = new Set([...(me.user.tour_state?.seen ?? []), ...ids]);
  setCached("me", { ...me, user: { ...me.user, tour_state: { seen: [...seen] } } });
}

/** Flush seen ids to the server; on failure park them in localStorage. */
function flush(ids: string[]) {
  if (ids.length === 0) return;
  mergeIntoCache(ids);
  const payload = [...new Set([...getPending(), ...ids])];
  setPending(payload);
  api
    .tourSeen(payload)
    .then(() => setPending([]))
    .catch(() => {
      // Stays in PENDING_KEY; merged into the unseen computation next load.
    });
}

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export function Tour({ page }: { page: TourPage }) {
  const [steps, setSteps] = useState<TourStep[] | null>(null);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const viewed = useRef<Set<string>>(new Set());
  const done = useRef(false);

  // Resolve unseen steps once per mount.
  useEffect(() => {
    let cancelled = false;

    async function resolve() {
      let seen: string[] | undefined;
      const cached = getCached<{ user: User }>("me");
      if (cached?.user?.tour_state) {
        seen = cached.user.tour_state.seen;
      } else {
        try {
          const me = await api.me();
          setCached("me", me);
          seen = me.user.tour_state?.seen;
        } catch {
          return; // can't know state — fail quiet, never re-nag
        }
      }
      if (seen === undefined) return; // API not migrated yet — fail quiet
      if (cancelled) return;
      const seenSet = new Set([...seen, ...getPending()]);
      const unseen = TOUR_REGISTRY.filter((s) => s.page === page && !seenSet.has(s.id));
      if (unseen.length > 0) setSteps(unseen);
    }

    resolve();
    return () => {
      cancelled = true;
    };
  }, [page]);

  const step = steps?.[index] ?? null;

  // Position the spotlight over the current step's anchor.
  useEffect(() => {
    if (!step) return;
    const el = document.querySelector(`[data-tour="${step.anchor}"]`);
    if (!el) {
      // Anchor not rendered (empty state, flagged-off feature) — skip it.
      viewed.current.add(step.id);
      setIndex((i) => i + 1);
      return;
    }
    viewed.current.add(step.id);
    el.scrollIntoView({ block: "center", behavior: "instant" as ScrollBehavior });

    const measure = () => {
      const r = el.getBoundingClientRect();
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    };
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [step]);

  // Run past the last step → finish.
  useEffect(() => {
    if (steps && index >= steps.length && !done.current) {
      done.current = true;
      flush([...viewed.current]);
      setSteps(null);
    }
  }, [steps, index]);

  // Flush whatever was viewed if the user navigates away mid-run.
  useEffect(() => {
    return () => {
      if (!done.current && viewed.current.size > 0) {
        done.current = true;
        flush([...viewed.current]);
      }
    };
  }, []);

  const skip = useCallback(() => {
    if (!steps) return;
    done.current = true;
    flush(steps.map((s) => s.id));
    setSteps(null);
  }, [steps]);

  if (!step || !rect) return null;

  const pad = 8;
  const radius = 20; // --r
  const cardBelow = rect.top + rect.height / 2 < window.innerHeight / 2;
  const isLast = index === (steps?.length ?? 0) - 1;

  return (
    <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label="Product tour">
      {/* Scrim with a spotlight cut-out */}
      <svg className="absolute inset-0 h-full w-full" style={{ transition: "opacity .25s" }}>
        <defs>
          <mask id="tour-spot">
            <rect width="100%" height="100%" fill="#fff" />
            <rect
              x={rect.left - pad}
              y={rect.top - pad}
              width={rect.width + pad * 2}
              height={rect.height + pad * 2}
              rx={radius}
              fill="#000"
              style={{ transition: "x .3s ease, y .3s ease, width .3s ease, height .3s ease" }}
            />
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgba(0,0,0,.55)" mask="url(#tour-spot)" />
      </svg>

      {/* Coachmark card */}
      <div
        className="glass-hi absolute mx-5 max-w-sm p-4"
        style={{
          borderRadius: "var(--r)",
          boxShadow: "var(--shc)",
          left: 0,
          right: 0,
          ...(cardBelow
            ? { top: Math.min(rect.top + rect.height + pad + 12, window.innerHeight - 220) }
            : { bottom: Math.max(window.innerHeight - rect.top + pad + 12, 96) }),
          transition: "top .3s ease, bottom .3s ease",
        }}
      >
        <div className="font-serif text-lg font-semibold">{step.title}</div>
        <p className="mt-1 text-[13px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
          {step.body}
        </p>
        <div className="mt-4 flex items-center justify-between">
          <div className="flex gap-1.5" aria-label={`Step ${index + 1} of ${steps!.length}`}>
            {steps!.map((s, i) => (
              <span
                key={s.id}
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: i <= index ? "var(--acc)" : "var(--brd-h)" }}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={skip} className="px-3 py-2 text-xs font-medium" style={{ color: "var(--txt-l)" }}>
              Skip tour
            </button>
            <button onClick={() => setIndex((i) => i + 1)} className="btn-primary px-5 py-2 text-sm">
              {isLast ? "Done" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
