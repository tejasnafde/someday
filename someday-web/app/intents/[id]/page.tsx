"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
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

  const [memorySheet, setMemorySheet] = useState(false);
  const [memoryNote, setMemoryNote] = useState("");
  const [memoryPhotos, setMemoryPhotos] = useState<File[]>([]);
  const [memoryUploading, setMemoryUploading] = useState(false);
  const photoInputRef = useRef<HTMLInputElement>(null);

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
    // Intercept transition to "done" to capture a memory
    if (s === "done" && intent!.task_status !== "done") {
      setMemoryNote("");
      setMemoryPhotos([]);
      setMemorySheet(true);
      return;
    }
    setIntent((prev) => (prev ? { ...prev, task_status: s } : prev));
    api.updateIntent(id, { task_status: s }).catch(() => load());
  }

  async function saveMemory() {
    setMemoryUploading(true);
    const urls: string[] = [];
    for (const file of memoryPhotos) {
      try {
        const res = await api.uploadMemoryPhoto(id, file);
        urls.push(res.url);
      } catch {
        // continue
      }
    }
    await api.updateIntent(id, {
      task_status: "done",
      done_note: memoryNote.trim() || undefined,
      done_photos: urls.length > 0 ? urls : undefined,
    });
    setMemoryUploading(false);
    setMemorySheet(false);
    load();
  }

  async function skipMemory() {
    await api.updateIntent(id, { task_status: "done" });
    setMemorySheet(false);
    setIntent((prev) => (prev ? { ...prev, task_status: "done" } : prev));
  }

  function addPhotos(files: FileList | null) {
    if (!files) return;
    const remaining = 4 - memoryPhotos.length;
    if (remaining <= 0) return;
    setMemoryPhotos((prev) => [...prev, ...Array.from(files).slice(0, remaining)]);
  }

  function removePhoto(i: number) {
    setMemoryPhotos((prev) => prev.filter((_, idx) => idx !== i));
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
  const hasMemory =
    intent.task_status === "done" &&
    (intent.done_note || (intent.done_photos && intent.done_photos.length > 0));

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
          <div className="tnum font-serif text-2xl font-semibold" style={{ color: "var(--acc)" }}>
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

      {hasMemory && (
        <div data-tour="intent-memories" className="glass mt-4 rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
          <div className="mb-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
            Memory
          </div>
          {intent.done_note && (
            <p className="font-serif text-sm italic leading-relaxed" style={{ color: "var(--txt-m)" }}>
              &ldquo;{intent.done_note}&rdquo;
            </p>
          )}
          {intent.done_photos && intent.done_photos.length > 0 && (
            <div className={`grid gap-2 ${intent.done_note ? "mt-3" : ""}`}
              style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
              {intent.done_photos.map((url, i) => (
                <img key={i} src={url} alt=""
                  className="aspect-square w-full object-cover"
                  style={{ borderRadius: "var(--rs)" }} />
              ))}
            </div>
          )}
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

      {memorySheet && (
        <div className="fixed inset-0 z-50 flex items-end" style={{ background: "rgba(0,0,0,.55)" }}>
          <div
            className="glass-hi w-full p-5"
            style={{
              borderRadius: "var(--r) var(--r) 0 0",
              paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 20px)",
            }}>
            <div className="mb-0.5 font-serif text-xl font-semibold leading-tight">You did it.</div>
            <div className="mb-4 text-sm" style={{ color: "var(--txt-m)" }}>
              How was it? Add a note and some photos.
            </div>

            <textarea
              value={memoryNote}
              onChange={(e) => setMemoryNote(e.target.value)}
              placeholder="We finally went…"
              rows={3}
              className="mb-4 w-full resize-none rounded-[var(--rs)] px-3.5 py-3 text-sm font-serif italic outline-none"
              style={{ background: "var(--glass-lo)", border: "1px solid var(--brd-s)", color: "var(--txt)" }}
            />

            <div className="mb-4 grid grid-cols-4 gap-2">
              {memoryPhotos.map((file, i) => (
                <div key={i} className="relative aspect-square">
                  <img
                    src={URL.createObjectURL(file)}
                    alt=""
                    className="h-full w-full object-cover"
                    style={{ borderRadius: "var(--rs)" }}
                  />
                  <button
                    type="button"
                    onClick={() => removePhoto(i)}
                    aria-label="Remove photo"
                    className="absolute right-0.5 top-0.5 flex h-5 w-5 items-center justify-center text-white"
                    style={{ background: "rgba(0,0,0,.6)", borderRadius: "var(--rs)", fontSize: 11, lineHeight: 1 }}>
                    &#215;
                  </button>
                </div>
              ))}
              {memoryPhotos.length < 4 && (
                <button
                  type="button"
                  onClick={() => photoInputRef.current?.click()}
                  aria-label="Add photo"
                  className="flex aspect-square items-center justify-center"
                  style={{
                    border: "1.5px dashed var(--brd-h)",
                    borderRadius: "var(--rs)",
                    color: "var(--txt-l)",
                  }}>
                  <Icon name="plus" />
                </button>
              )}
            </div>
            <input
              ref={photoInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              className="hidden"
              onChange={(e) => addPhotos(e.target.files)}
            />

            <div className="flex gap-2.5">
              <button
                onClick={saveMemory}
                disabled={memoryUploading}
                className="btn-primary flex-1 py-3 text-sm disabled:opacity-60">
                {memoryUploading ? "Saving…" : "Save memory"}
              </button>
              <button
                onClick={skipMemory}
                disabled={memoryUploading}
                className="btn-ghost px-5 py-3 text-sm disabled:opacity-50">
                Skip
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
