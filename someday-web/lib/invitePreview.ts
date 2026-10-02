// Server-side lookup for /join link previews (page metadata and OG image).
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type InvitePreview = { circle_name: string; inviter_name: string | null };

export async function getInvitePreview(token: string): Promise<InvitePreview | null> {
  try {
    const res = await fetch(`${BASE}/circles/invite/${encodeURIComponent(token)}`, {
      next: { revalidate: 300 },
    });
    return res.ok ? await res.json() : null;
  } catch {
    // ponytail: a failed lookup only costs the rich preview; the generic one still renders.
    return null;
  }
}

export function inviteTitle(p: InvitePreview | null): string {
  if (!p) return "You're invited to Someday";
  return p.inviter_name
    ? `${p.inviter_name} invited you to ${p.circle_name} on Someday`
    : `You're invited to ${p.circle_name} on Someday`;
}
