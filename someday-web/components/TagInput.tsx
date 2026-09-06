"use client";

import { useRef, useState } from "react";
import { Icon } from "@/components/Sprite";

/**
 * Chip-builder tag input. Comma, Tab, or Enter commits a chip; Backspace on an
 * empty input removes the last one. Suggestions come from the circle's
 * existing tags so names stay consistent. Values are normalized (lowercase,
 * trimmed) to match the server's canonical form.
 */
export function TagInput({ value, onChange, suggestions, placeholder }: {
  value: string[];
  onChange: (tags: string[]) => void;
  suggestions: string[];
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function commit(raw: string) {
    const tag = raw.trim().toLowerCase().replace(/,+$/, "").replace(/\s+/g, " ");
    if (tag && !value.includes(tag)) onChange([...value, tag]);
    setDraft("");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if ((e.key === "Enter" || e.key === "," || e.key === "Tab") && draft.trim()) {
      e.preventDefault();
      commit(draft);
    } else if (e.key === "Backspace" && !draft && value.length > 0) {
      onChange(value.slice(0, -1));
    } else if (e.key === "Enter" && !draft.trim()) {
      // Empty Enter must not submit the surrounding form by surprise.
      e.preventDefault();
    }
  }

  const q = draft.trim().toLowerCase();
  const matches = suggestions
    .filter((s) => !value.includes(s) && (!q || s.includes(q)))
    .slice(0, 6);
  const canCreate = !!q && !suggestions.includes(q) && !value.includes(q);
  const open = focused && (matches.length > 0 || canCreate);

  return (
    <div className="relative">
      <div
        onClick={() => inputRef.current?.focus()}
        className="glass flex w-full cursor-text flex-wrap items-center gap-1.5 rounded-[var(--rs)] px-3 py-2.5"
      >
        {value.map((t) => (
          <span key={t} className="flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold"
            style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
            {t}
            <button type="button" aria-label={`Remove ${t}`}
              onClick={() => onChange(value.filter((v) => v !== t))}
              className="flex items-center" style={{ color: "var(--acc)" }}>
              <Icon name="x" size="sm" />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          placeholder={value.length === 0 ? placeholder ?? "Type to add tags" : ""}
          className="min-w-[110px] flex-1 bg-transparent py-0.5 text-sm outline-none"
          style={{ color: "var(--txt)" }}
        />
      </div>
      {open && (
        <div className="glass-hi absolute inset-x-0 top-full z-20 mt-1.5 rounded-[var(--rs)] p-1.5"
          style={{ boxShadow: "var(--shc)" }}>
          {matches.map((s) => (
            <button key={s} type="button"
              onMouseDown={(e) => { e.preventDefault(); commit(s); }}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px]"
              style={{ color: "var(--txt)" }}>
              <span style={{ color: "var(--txt-l)" }}><Icon name="plus" size="sm" /></span>
              {s}
            </button>
          ))}
          {canCreate && (
            <button type="button"
              onMouseDown={(e) => { e.preventDefault(); commit(q); }}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px] font-semibold"
              style={{ color: "var(--acc)" }}>
              <Icon name="plus" size="sm" />
              Create &ldquo;{q}&rdquo;
            </button>
          )}
        </div>
      )}
    </div>
  );
}
