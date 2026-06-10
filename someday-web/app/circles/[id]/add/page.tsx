"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { CATEGORY_ICONS, NavBar } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { Category, LinkMeta } from "@/lib/types";

const CATEGORIES: Category[] = ["watch", "eat", "visit", "read", "play", "trip"];

export default function AddIntent() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [tags, setTags] = useState("");
  const [category, setCategory] = useState<Category | null>(null);
  const [preview, setPreview] = useState<LinkMeta | null>(null);
  const [unfurling, setUnfurling] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!url.match(/^https?:\/\/.+\..+/)) {
      setPreview(null);
      return;
    }
    const t = setTimeout(async () => {
      setUnfurling(true);
      try {
        const meta = await api.unfurl(url);
        setPreview(meta);
        if (meta.title && !title) setTitle(meta.title);
      } catch {
        setPreview(null);
      }
      setUnfurling(false);
    }, 600);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.createIntent(id, {
        title: title.trim(),
        url: url || undefined,
        note: note || undefined,
        category: category ?? undefined,
        tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : undefined,
      });
      router.push(`/circles/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
      setBusy(false);
    }
  }

  if (!ready) return null;

  const label = "mb-2 block text-[11px] font-semibold uppercase tracking-wider";
  const input = "glass w-full rounded-[var(--rs)] px-3.5 py-3 text-sm outline-none";

  return (
    <main>
      <NavBar title="Save to circle" back={`/circles/${id}`} />

      <form onSubmit={save} className="flex flex-col gap-5">
        <div>
          <label className={label} style={{ color: "var(--txt-l)" }}>Link</label>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Paste a link (optional)" className={input} />
        </div>

        {(unfurling || preview) && (
          <div className="overflow-hidden" style={{ borderRadius: "var(--r)", border: "1px solid var(--brd-h)" }}>
            {unfurling ? (
              <div className="glass-hi flex h-24 items-center justify-center text-xs" style={{ color: "var(--txt-l)" }}>
                Fetching preview…
              </div>
            ) : preview?.image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview.image} alt="" className="h-32 w-full object-cover" />
            ) : null}
            {preview && !unfurling && (
              <div className="glass-hi p-3.5" style={{ border: "none" }}>
                {preview.site && (
                  <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
                    {preview.site}
                  </div>
                )}
                <div className="mt-0.5 font-serif text-sm font-medium">{preview.title}</div>
              </div>
            )}
          </div>
        )}

        <div>
          <label className={label} style={{ color: "var(--txt-l)" }}>Title</label>
          <input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What's the plan?" className={input} />
        </div>

        <div>
          <label className={label} style={{ color: "var(--txt-l)" }}>Category</label>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button key={c} type="button" onClick={() => setCategory(category === c ? null : c)}
                className="flex items-center gap-1.5 rounded-[var(--rs)] px-3 py-2 text-xs font-medium capitalize"
                style={{
                  background: category === c ? "var(--acc-l)" : "var(--glass-lo)",
                  border: `1px solid ${category === c ? "var(--acc)44" : "var(--brd-s)"}`,
                  color: category === c ? "var(--acc)" : "var(--txt-m)",
                }}>
                <Icon name={CATEGORY_ICONS[c]} size="sm" />
                {c}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className={label} style={{ color: "var(--txt-l)" }}>Note</label>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why this? (optional)"
            className={`${input} h-20 resize-none font-serif italic`} />
        </div>

        <div>
          <label className={label} style={{ color: "var(--txt-l)" }}>Tags</label>
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="comma, separated (optional)" className={input} />
        </div>

        {error && <div className="text-sm" style={{ color: "var(--cp)" }}>{error}</div>}

        <button type="submit" disabled={busy || !title.trim()} className="btn-primary mb-8 w-full py-3.5 text-sm disabled:opacity-60">
          {busy ? "Saving…" : "Save to Circle"}
        </button>
      </form>
    </main>
  );
}
