"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { Tour } from "@/components/Tour";
import { CATEGORY_ICONS, IntentPreview, NavBar, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { Category, Intent, TaskStatus } from "@/lib/types";

const STEPS: TaskStatus[] = ["saved", "interested", "planned", "done"];
const CATEGORIES: Category[] = ["watch", "eat", "visit", "read", "play", "trip", "talk"];

export default function IntentPage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [intent, setIntent] = useState<Intent | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ title: "", note: "", tags: "", category: null as Category | null, planned_for: "" });
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api.intent(id).then(setIntent);
  }, [id]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  if (!ready || !intent) return <Spinner />;

  function startEdit() {
    setForm({
      title: intent!.title,
      note: intent!.note ?? "",
      tags: intent!.tags.join(", "),
      category: intent!.category,
      planned_for: intent!.planned_for ?? "",
    });
    setEditing(true);
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    await api.updateIntent(id, {
      title: form.title.trim(),
      note: form.note.trim() || undefined,
      category: form.category ?? undefined,
      tags: form.tags ? form.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      planned_for: form.planned_for.trim() || undefined,
    });
    setSaving(false);
    setEditing(false);
    load();
  }

  function setStatus(s: TaskStatus) {
    setIntent((prev) => (prev ? { ...prev, task_status: s } : prev));
    api.updateIntent(id, { task_status: s }).catch(() => load());
  }

  function react() {
    setIntent((prev) =>
      prev
        ? {
            ...prev,
            reacted_by_me: !prev.reacted_by_me,
            reaction_count: prev.reaction_count + (prev.reacted_by_me ? -1 : 1),
          }
        : prev,
    );
    api.react(id).catch(() => load());
  }

  function boost() {
    setIntent((prev) => (prev ? { ...prev, boosted_by_me: !prev.boosted_by_me } : prev));
    api.boost(id).catch(() => load());
  }

  async function remove() {
    if (!confirm("Delete this from the circle?")) return;
    await api.deleteIntent(id);
    router.push(`/circles/${intent!.circle_id}`);
  }

  const label = "mb-2 block text-[11px] font-semibold uppercase tracking-wider";
  const input = "glass w-full rounded-[var(--rs)] px-3.5 py-3 text-sm outline-none";

  if (editing) {
    return (
      <main>
        <NavBar title="Edit" back={`/circles/${intent.circle_id}`} />
        <form onSubmit={saveEdit} className="flex flex-col gap-5">
          <div>
            <label className={label} style={{ color: "var(--txt-l)" }}>Title</label>
            <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={input} />
          </div>
          <div>
            <label className={label} style={{ color: "var(--txt-l)" }}>Category</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((c) => (
                <button key={c} type="button"
                  onClick={() => setForm({ ...form, category: form.category === c ? null : c })}
                  className="flex items-center gap-1.5 rounded-[var(--rs)] px-3 py-2 text-xs font-medium capitalize"
                  style={{
                    background: form.category === c ? "var(--acc-l)" : "var(--glass-lo)",
                    border: `1px solid ${form.category === c ? "var(--acc)44" : "var(--brd-s)"}`,
                    color: form.category === c ? "var(--acc)" : "var(--txt-m)",
                  }}>
                  <Icon name={CATEGORY_ICONS[c]} size="sm" />
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className={label} style={{ color: "var(--txt-l)" }}>Note</label>
            <textarea value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })}
              className={`${input} h-20 resize-none font-serif italic`} />
          </div>
          <div>
            <label className={label} style={{ color: "var(--txt-l)" }}>Tags</label>
            <input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })}
              placeholder="comma, separated" className={input} />
          </div>
          <div>
            <label className={label} style={{ color: "var(--txt-l)" }}>When</label>
            <input value={form.planned_for} onChange={(e) => setForm({ ...form, planned_for: e.target.value })}
              placeholder="next weekend, after exams, someday…" className={input} />
          </div>
          <div className="mb-8 flex gap-2.5">
            <button type="submit" disabled={saving || !form.title.trim()} className="btn-primary flex-1 py-3 text-sm disabled:opacity-60">
              {saving ? "Saving…" : "Save changes"}
            </button>
            <button type="button" onClick={() => setEditing(false)} className="btn-ghost px-5 py-3 text-sm">
              Cancel
            </button>
          </div>
        </form>
      </main>
    );
  }

  return (
    <main>
      <NavBar title="Intent" back={`/circles/${intent.circle_id}`}
        right={
          <div className="flex items-center gap-2">
            <button onClick={startEdit} aria-label="Edit"
              className="glass flex h-9 w-9 items-center justify-center rounded-full" style={{ color: "var(--txt-m)" }}>
              <Icon name="pencil" size="sm" />
            </button>
            <button onClick={remove} aria-label="Delete"
              className="glass flex h-9 w-9 items-center justify-center rounded-full" style={{ color: "var(--cp)" }}>
              <Icon name="trash" size="sm" />
            </button>
          </div>
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
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {intent.url && (
              <a href={intent.url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--acc)" }}>
                <Icon name="link" size="sm" />
                Open link
              </a>
            )}
            {intent.planned_for && (
              <span data-tour="intent-planned" className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--sp-t)" }}>
                <Icon name="clock" size="sm" />
                {intent.planned_for}
              </span>
            )}
          </div>
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
        <button onClick={react} className="btn-primary flex-1 py-3 text-sm"
          style={intent.reacted_by_me ? { opacity: 0.85 } : undefined}>
          <Icon name="heart" size="sm" />
          {intent.reacted_by_me ? "Interested ✓" : "Interested"}
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
        <div className="mb-8 mt-4 flex flex-wrap gap-1.5">
          {intent.tags.map((t) => (
            <span key={t} className="rounded-full px-2.5 py-1 text-[11px]"
              style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
              {t}
            </span>
          ))}
        </div>
      )}
      <Tour page="intent" />
    </main>
  );
}
