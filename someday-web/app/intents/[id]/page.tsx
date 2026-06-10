"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { IntentPreview, NavBar, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { Intent, TaskStatus } from "@/lib/types";

const STEPS: TaskStatus[] = ["saved", "interested", "planned", "done"];

export default function IntentPage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [intent, setIntent] = useState<Intent | null>(null);

  const load = useCallback(() => {
    api.intent(id).then(setIntent);
  }, [id]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  if (!ready || !intent) return <Spinner />;

  async function setStatus(s: TaskStatus) {
    await api.updateIntent(id, { task_status: s });
    load();
  }

  async function react() {
    await api.react(id);
    load();
  }

  async function boost() {
    await api.boost(id);
    load();
  }

  async function remove() {
    await api.deleteIntent(id);
    router.push(`/circles/${intent!.circle_id}`);
  }

  return (
    <main>
      <NavBar title="Intent" back={`/circles/${intent.circle_id}`}
        right={
          <button onClick={remove} aria-label="Delete"
            className="glass flex h-9 w-9 items-center justify-center rounded-full" style={{ color: "var(--cp)" }}>
            <Icon name="trash" size="sm" />
          </button>
        }
      />

      <div className="overflow-hidden" style={{ borderRadius: "var(--r)", boxShadow: "var(--shc)" }}>
        <IntentPreview intent={intent} height={160} />
        <div className="glass-hi p-4" style={{ border: "none" }}>
          {intent.link_meta?.site && (
            <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
              {intent.link_meta.site}
            </div>
          )}
          <h1 className="mt-0.5 font-serif text-lg font-semibold leading-snug">{intent.title}</h1>
          {intent.url && (
            <a href={intent.url} target="_blank" rel="noreferrer"
              className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--acc)" }}>
              <Icon name="link" size="sm" />
              Open link
            </a>
          )}
        </div>
      </div>

      <div className="glass mt-4 flex items-center gap-3 rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
        <div>
          <div className="font-serif text-2xl font-semibold" style={{ color: "var(--acc)" }}>
            {intent.reaction_count}
          </div>
          <div className="text-xs" style={{ color: "var(--txt-m)" }}>
            {intent.reaction_count === 1 ? "member" : "members"} interested
          </div>
        </div>
      </div>

      <div className="glass mt-3 rounded-[var(--r)] p-3.5" style={{ boxShadow: "var(--shc)" }}>
        <div className="mb-2.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
          Status
        </div>
        <div className="flex items-center">
          {STEPS.map((s, i) => (
            <span key={s} className="contents">
              {i > 0 && <span className="h-px w-3" style={{ background: "var(--brd-s)" }} />}
              <button onClick={() => setStatus(s)}
                className="flex-1 rounded-lg px-1 py-2 text-[10px] font-medium capitalize"
                style={{
                  background: intent.task_status === s ? "var(--acc-l)" : "transparent",
                  color: intent.task_status === s ? "var(--acc)" : "var(--txt-l)",
                  fontWeight: intent.task_status === s ? 700 : 500,
                }}>
                {s}
              </button>
            </span>
          ))}
        </div>
      </div>

      <div className="mt-4 flex gap-2.5">
        <button onClick={react} className="btn-primary flex-1 py-3 text-sm">
          <Icon name="heart" size="sm" />
          Interested
        </button>
        <button onClick={boost} className="btn-ghost px-5 py-3 text-sm"
          style={intent.boosted_by_me ? { color: "#B89000", borderColor: "rgba(234,165,0,.4)" } : undefined}>
          <Icon name="zap" size="sm" />
          Boost
        </button>
      </div>

      {intent.note && (
        <div className="glass mt-4 rounded-[var(--r)] p-4">
          <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
            Note
          </div>
          <div className="font-serif text-sm italic" style={{ color: "var(--txt-m)" }}>
            &ldquo;{intent.note}&rdquo;
          </div>
        </div>
      )}

      {intent.tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {intent.tags.map((t) => (
            <span key={t} className="rounded-full px-2.5 py-1 text-[11px]"
              style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </main>
  );
}
