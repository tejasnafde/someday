"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { Tour } from "@/components/Tour";
import {
  CircleAvatar,
  MemberDot,
  NavBar,
  Skeleton,
  circleTheme,
  memberColor,
} from "@/components/ui";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/useAuth";
import type { CircleDetail, Member } from "@/lib/types";

export default function MembersPage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [me, setMe] = useState("");
  const [sheet, setSheet] = useState<Member | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => api.circle(id).then(setCircle), [id]);

  useEffect(() => {
    if (!ready) return;
    load();
    supabase.auth.getSession().then(({ data }) => setMe(data.session?.user.id ?? ""));
  }, [ready, load]);

  if (!ready || !circle)
    return (
      <main>
        <NavBar title="Members" back={`/circles/${id}`} />
        <Skeleton height={64} count={4} />
      </main>
    );

  const theme = circleTheme(circle.id);
  const myRole = circle.members.find((m) => m.user_id === me)?.role ?? "member";
  const canManage = myRole === "owner" || myRole === "admin";

  function actionsFor(m: Member): { label: string; danger?: boolean; onClick: () => void }[] {
    const actions: { label: string; danger?: boolean; onClick: () => void }[] = [];
    if (m.user_id === me || m.role === "owner") return actions;
    if (!canManage) return actions;
    const targetIsAdmin = m.role === "admin";
    if (targetIsAdmin && myRole === "owner")
      actions.push({ label: "Demote to member", onClick: () => changeRole(m, "member") });
    if (!targetIsAdmin)
      actions.push({ label: "Make admin", onClick: () => changeRole(m, "admin") });
    if (myRole === "owner" && !targetIsAdmin)
      actions.push({ label: "Make owner", onClick: () => transferOwnership(m) });
    if (!(targetIsAdmin && myRole === "admin"))
      actions.push({ label: "Remove from circle", danger: true, onClick: () => removeMember(m) });
    return actions;
  }

  async function changeRole(m: Member, role: "admin" | "member") {
    setBusy(true);
    try {
      await api.setMemberRole(id, m.user_id, role);
      setSheet(null);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function transferOwnership(m: Member) {
    if (!confirm(`Make ${m.display_name ?? "this member"} the owner? You'll become an admin.`)) return;
    setBusy(true);
    try {
      await api.setMemberRole(id, m.user_id, "owner");
      setSheet(null);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function removeMember(m: Member) {
    if (!confirm(`Remove ${m.display_name ?? "this member"} from the circle?`)) return;
    setBusy(true);
    try {
      await api.removeMember(id, m.user_id);
      setSheet(null);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function leaveCircle() {
    if (myRole === "owner") {
      alert("Transfer ownership before leaving - promote another member first.");
      return;
    }
    if (!confirm("Leave this circle?")) return;
    await api.leaveCircle(id);
    router.push("/");
  }

  async function deleteCircle() {
    if (!confirm("Delete this circle for everyone? This can't be undone.")) return;
    await api.deleteCircle(id);
    router.push("/");
  }

  async function copyInvite() {
    await navigator.clipboard.writeText(`${location.origin}/join/${circle!.invite_token}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <main>
      <NavBar
        title="Members"
        subtitle={`${circle.name} · ${circle.member_count} ${circle.member_count === 1 ? "person" : "people"}`}
        back={`/circles/${id}`}
      />

      <div className="glass mb-4 flex items-center gap-4 rounded-[var(--r)] p-3.5" style={{ boxShadow: "var(--shc)" }}>
        <CircleAvatar circleId={circle.id} themeKey={theme.key} icon={theme.icon} size={52} />
        <div className="min-w-0 flex-1">
          <div className="truncate font-serif text-base font-semibold">{circle.name}</div>
          <div className="tnum text-xs" style={{ color: "var(--txt-m)" }}>
            {circle.open_intent_count} {circle.open_intent_count === 1 ? "idea waiting" : "ideas waiting"}
          </div>
        </div>
      </div>

      <div className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-l)" }}>
        People
      </div>
      <div data-tour="members-list" className="mb-5 flex flex-col gap-2">
        {circle.members.map((m, i) => {
          const acts = actionsFor(m);
          return (
            <button
              key={m.user_id}
              onClick={() => (acts.length ? setSheet(m) : undefined)}
              disabled={!acts.length}
              className="glass flex items-center gap-3 rounded-[var(--rs)] p-3 text-left disabled:cursor-default"
              style={{ border: m.user_id === me ? "1px solid rgba(155,141,196,.30)" : undefined }}
            >
              <MemberDot name={m.display_name ?? m.email} color={memberColor(i)} size={42} src={m.avatar_url} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5 text-sm font-semibold">
                  <span className="truncate">{m.display_name ?? m.email}</span>
                  {m.role === "owner" && (
                    <span className="rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                      style={{ background: "var(--acc-l)", color: "var(--acc)" }}>Owner</span>
                  )}
                  {m.role === "admin" && (
                    <span className="rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                      style={{ background: "rgba(45,191,138,.13)", color: "var(--sp-t)" }}>Admin</span>
                  )}
                  {m.user_id === me && (
                    <span className="rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                      style={{ background: "var(--glass-lo)", color: "var(--txt-m)", border: "1px solid var(--brd-s)" }}>You</span>
                  )}
                </div>
                <div className="truncate text-xs" style={{ color: "var(--txt-m)" }}>{m.email}</div>
              </div>
              {acts.length > 0 && (
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                  style={{ background: "var(--glass-lo)", color: "var(--txt-m)", border: "1px solid var(--brd-s)" }}>
                  <Icon name="more" size="sm" />
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="rounded-[var(--r)] p-4"
        style={{ background: "linear-gradient(135deg, var(--acc-l), rgba(189,176,224,.04))", border: "1px solid rgba(155,141,196,.22)" }}>
        <div className="font-serif text-base font-semibold">Bring someone in</div>
        <div className="mb-3 mt-1 text-xs" style={{ color: "var(--txt-m)" }}>Anyone with the link can join.</div>
        <div className="mb-2.5 truncate rounded-[var(--rs)] px-3 py-2 font-mono text-[11px]"
          style={{ background: "var(--glass-lo)", color: "var(--txt-m)", border: "1px solid var(--brd-s)" }}>
          {`${typeof location !== "undefined" ? location.origin : ""}/join/${circle.invite_token}`}
        </div>
        <button onClick={copyInvite} className="btn-primary w-full py-2.5 text-sm">
          <Icon name={copied ? "check" : "copy"} size="sm" />
          {copied ? "Copied" : "Copy invite link"}
        </button>
      </div>

      <div className="mb-8 mt-7 flex justify-center gap-7 text-xs font-medium" style={{ color: "var(--txt-l)" }}>
        {myRole !== "owner" && (
          <button onClick={leaveCircle} className="flex items-center gap-1.5">
            <Icon name="log-out" size="sm" />Leave circle
          </button>
        )}
        {myRole === "owner" && (
          <button onClick={deleteCircle} className="flex items-center gap-1.5" style={{ color: "var(--cp)" }}>
            <Icon name="trash" size="sm" />Delete circle
          </button>
        )}
      </div>

      <Tour page="members" />

      {sheet && (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
          style={{ background: "rgba(0,0,0,.4)" }} onClick={() => setSheet(null)}>
          <div className="glass-hi mx-4 mb-6 w-full max-w-sm rounded-[var(--r)] p-5 sm:mb-0"
            style={{ boxShadow: "var(--shc)" }} onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center gap-3 border-b pb-4" style={{ borderColor: "var(--brd-s)" }}>
              <MemberDot
                name={sheet.display_name ?? sheet.email}
                color={memberColor(circle.members.findIndex((x) => x.user_id === sheet.user_id))}
                size={44}
                src={sheet.avatar_url}
              />
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">{sheet.display_name ?? sheet.email}</div>
                <div className="truncate text-xs" style={{ color: "var(--txt-m)" }}>{sheet.email}</div>
              </div>
              <button onClick={() => setSheet(null)} aria-label="Close"
                className="glass flex h-8 w-8 shrink-0 items-center justify-center rounded-full" style={{ color: "var(--txt-m)" }}>
                <Icon name="x" size="sm" />
              </button>
            </div>
            <div className="flex flex-col">
              {actionsFor(sheet).map((a, i) => (
                <button key={i} disabled={busy} onClick={a.onClick}
                  className="flex items-center justify-between rounded-[var(--rs)] px-3 py-3.5 text-left text-sm font-medium disabled:opacity-50"
                  style={{ color: a.danger ? "var(--cp)" : "var(--txt)" }}>
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
