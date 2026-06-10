"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { IntentPreview, NavBar, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { CircleDetail, SmartPick, SpinItem } from "@/lib/types";

export default function PayoffPage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [shortlistCount, setShortlistCount] = useState<number | null>(null);
  const [pick, setPick] = useState<SmartPick | null>(null);
  const [spinItems, setSpinItems] = useState<SpinItem[] | null>(null);
  const [spinning, setSpinning] = useState(false);
  const [winner, setWinner] = useState<SpinItem | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ready) return;
    api.circle(id).then(setCircle);
    api.intents(id, { shortlist: true }).then((l) => setShortlistCount(l.length));
  }, [ready, id]);

  async function bestPick() {
    setBusy(true);
    setError("");
    setWinner(null);
    setSpinItems(null);
    try {
      setPick(await api.smartPick(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No shortlist yet");
    }
    setBusy(false);
  }

  async function spin() {
    setBusy(true);
    setError("");
    setPick(null);
    setWinner(null);
    try {
      const { shortlist } = await api.spin(id);
      setSpinItems(shortlist);
      setSpinning(true);
      setTimeout(() => {
        setSpinning(false);
        setWinner(shortlist[0]);
      }, 2600);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No shortlist yet");
    }
    setBusy(false);
  }

  async function markPlanned(intentId: string) {
    await api.updateIntent(intentId, { task_status: "planned" });
    setPick(null);
    setWinner(null);
  }

  if (!ready || !circle) return <Spinner />;

  return (
    <main>
      <NavBar title="Payoff" back={`/circles/${id}`} />

      <div className="py-4 text-center">
        <h1 className="font-serif text-[28px] font-medium leading-tight">
          What are you doing<br /><em style={{ color: "var(--acc)" }}>today?</em>
        </h1>
        <p className="mt-2 text-[13px]" style={{ color: "var(--txt-m)" }}>
          {circle.member_count > 1 ? "You're together. Time to pick." : "Invite someone first — this works better together."}
        </p>
        {shortlistCount !== null && (
          <span className="mt-2.5 inline-block rounded-full px-3.5 py-1.5 text-xs font-semibold"
            style={{ background: "var(--acc-l)", color: "var(--acc)", border: "1.5px solid var(--acc)33" }}>
            {shortlistCount} {shortlistCount === 1 ? "thing" : "things"} you both want
          </span>
        )}
      </div>

      <div className="mt-2 flex flex-col gap-3">
        <button onClick={bestPick} disabled={busy} className="btn-primary w-full py-4 text-[15px] disabled:opacity-60">
          <Icon name="target" />
          Best Pick
        </button>
        <button onClick={spin} disabled={busy || spinning} className="btn-ghost w-full py-4 text-[15px] disabled:opacity-60">
          <Icon name="shuffle" />
          Spin the Wheel
        </button>
      </div>

      {error && (
        <div className="glass mt-5 rounded-[var(--r)] p-4 text-center text-sm" style={{ color: "var(--txt-m)" }}>
          {error}
        </div>
      )}

      {spinning && spinItems && (
        <div className="mt-6 overflow-hidden" style={{ borderRadius: "var(--r)", height: 96, boxShadow: "var(--shc)" }}>
          <div className="animate-[reel_2.6s_cubic-bezier(.15,.85,.25,1)_forwards]">
            {[...spinItems.slice(1), ...spinItems, ...spinItems].map((s, i) => (
              <div key={i} className="glass-hi flex h-24 items-center justify-center px-6 font-serif font-semibold" style={{ border: "none" }}>
                {s.title}
              </div>
            ))}
          </div>
          <style>{`@keyframes reel { from { transform: translateY(0) } to { transform: translateY(-${(spinItems.length * 2 - 1) * 96}px) } }`}</style>
        </div>
      )}

      {pick && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2.5 text-[10px] font-semibold uppercase tracking-[.12em]" style={{ color: "var(--txt-l)" }}>
            <span className="h-px flex-1" style={{ background: "var(--brd-s)" }} />
            Best Pick
            <span className="h-px flex-1" style={{ background: "var(--brd-s)" }} />
          </div>
          <div className="overflow-hidden" style={{ borderRadius: "var(--r)", border: "1px solid var(--acc)33", boxShadow: "0 8px 40px var(--acc-glow), var(--shc)" }}>
            <IntentPreview intent={{ category: null, link_meta: pick.link_meta }} height={128} />
            <div className="glass-hi p-4" style={{ border: "none" }}>
              <div className="font-serif text-lg font-semibold">{pick.title}</div>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                <Chip icon="heart" label={`${pick.breakdown.reaction_count} of ${circle.member_count} interested`} />
                <Chip icon="clock" label={`Saved ${Math.round(pick.breakdown.days_saved)} days ago`} />
                {pick.breakdown.has_boost && <Chip icon="zap" label="Boosted today" />}
              </div>
              <button onClick={() => markPlanned(pick.intent_id)} className="btn-primary mt-4 w-full py-3 text-sm" style={{ borderRadius: "var(--rs)" }}>
                <Icon name="check" size="sm" />
                Mark as Planned
              </button>
            </div>
          </div>
        </div>
      )}

      {winner && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2.5 text-[10px] font-semibold uppercase tracking-[.12em]" style={{ color: "var(--txt-l)" }}>
            <span className="h-px flex-1" style={{ background: "var(--brd-s)" }} />
            The wheel has spoken
            <span className="h-px flex-1" style={{ background: "var(--brd-s)" }} />
          </div>
          <div className="overflow-hidden" style={{ borderRadius: "var(--r)", border: "1px solid var(--acc)33", boxShadow: "0 8px 40px var(--acc-glow), var(--shc)" }}>
            <IntentPreview intent={{ category: winner.category, link_meta: winner.link_meta }} height={128} />
            <div className="glass-hi p-4" style={{ border: "none" }}>
              <div className="font-serif text-lg font-semibold">{winner.title}</div>
              <button onClick={() => markPlanned(winner.id)} className="btn-primary mt-4 w-full py-3 text-sm" style={{ borderRadius: "var(--rs)" }}>
                <Icon name="check" size="sm" />
                Mark as Planned
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function Chip({ icon, label }: { icon: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium"
      style={{ background: "var(--acc-l)", color: "var(--acc)", border: "1px solid var(--acc)22" }}>
      <Icon name={icon} size="sm" />
      {label}
    </span>
  );
}
