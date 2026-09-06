import { supabase } from "./supabase";
import type { AppNotification, Circle, CircleDetail, Intent, LinkMeta, Moment, NotificationFeed, SmartPick, SpinItem, TourState, User } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CLIENT_HEADERS = { "X-Someday-Client": "web" };

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const TIMEOUT_MS = 15000;

// Reject a request that hasn't settled in 15s so a hung fetch or stalled
// getSession() can't leave a caller's loading state stuck forever.
// ponytail: races the whole op; the underlying fetch may run to completion.
function withTimeout<T>(work: Promise<T>, label: string): Promise<T> {
  return Promise.race([
    work,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new ApiError(0, `${label} timed out`)), TIMEOUT_MS),
    ),
  ]);
}

function upload<T>(path: string, blob: Blob, filename: string): Promise<T> {
  return withTimeout((async (): Promise<T> => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) throw new ApiError(401, "Not signed in");
    const form = new FormData();
    form.append("file", blob, filename);
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { ...CLIENT_HEADERS, Authorization: `Bearer ${token}` },
      body: form,
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, json.message ?? json.detail ?? res.statusText);
    return json as T;
  })(), `POST ${path}`);
}

function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  return withTimeout((async (): Promise<T> => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) throw new ApiError(401, "Not signed in");

    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: {
        ...CLIENT_HEADERS,
        Authorization: `Bearer ${token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, json.message ?? json.detail ?? res.statusText);
    return json as T;
  })(), `${method} ${path}`);
}

export const api = {
  verify: () => request<{ user: User }>("POST", "/auth/verify"),
  me: () => request<{ user: User; circles: Circle[] }>("GET", "/auth/me"),
  updateMe: (fields: { display_name?: string; avatar_url?: string }) =>
    request<{ user: User }>("PATCH", "/auth/me", fields),
  uploadAvatar: (blob: Blob) => upload<{ user: User }>("/auth/me/avatar", blob, "avatar.webp"),
  uploadCirclePhoto: (circleId: string, blob: Blob) =>
    upload<{ photo_url: string }>(`/circles/${circleId}/photo`, blob, "photo.webp"),

  circles: () => request<Circle[]>("GET", "/circles"),
  circle: (id: string) => request<CircleDetail>("GET", `/circles/${id}`),
  createCircle: (name: string, emoji?: string) =>
    request<Circle>("POST", "/circles", { name, emoji }),
  updateCircle: (id: string, fields: { name?: string; emoji?: string; moments_cadence?: number }) =>
    request<Circle>("PATCH", `/circles/${id}`, fields),
  deleteCircle: (id: string) => request<unknown>("DELETE", `/circles/${id}`),
  joinCircle: (token: string) =>
    request<{ message: string; circle_id: string; name: string }>("POST", `/circles/join/${token}`),
  leaveCircle: (id: string) => request<unknown>("POST", `/circles/${id}/leave`),

  intents: (circleId: string, params?: { task_status?: string; category?: string; tag?: string; tags?: string[]; shortlist?: boolean; cursor?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.task_status) q.set("task_status", params.task_status);
    if (params?.category) q.set("category", params.category);
    if (params?.tag) q.set("tag", params.tag);
    for (const t of params?.tags ?? []) q.append("tags", t);
    if (params?.shortlist) q.set("shortlist", "true");
    if (params?.cursor) q.set("cursor", params.cursor);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<{ items: Intent[]; next_cursor: string | null }>("GET", `/circles/${circleId}/intents${qs ? `?${qs}` : ""}`);
  },
  rotateInvite: (circleId: string) =>
    request<{ invite_token: string }>("POST", `/circles/${circleId}/rotate-invite`),
  clientError: (context: string, message: string, detail?: string) =>
    fetch(`${BASE}/auth/client-error`, {
      method: "POST",
      headers: { ...CLIENT_HEADERS, "Content-Type": "application/json" },
      body: JSON.stringify({ context, message, detail }),
    }).catch(() => {}), // fire-and-forget, never throws
  circleTags: (circleId: string) => request<string[]>("GET", `/circles/${circleId}/tags`),
  moments: (circleId: string, cursor?: string) =>
    request<{ items: Moment[]; next_cursor: string | null }>(
      "GET", `/circles/${circleId}/moments${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`),
  moment: (id: string) => request<Moment>("GET", `/moments/${id}`),
  postMoment: (momentId: string, blob: Blob, caption: string): Promise<Moment> =>
    withTimeout((async (): Promise<Moment> => {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) throw new ApiError(401, "Not signed in");
      const form = new FormData();
      form.append("photo", blob, "moment.webp");
      if (caption.trim()) form.append("caption", caption.trim());
      const res = await fetch(`${BASE}/moments/${momentId}/posts`, {
        method: "POST",
        headers: { ...CLIENT_HEADERS, Authorization: `Bearer ${token}` },
        body: form,
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new ApiError(res.status, json.message ?? json.detail ?? res.statusText);
      return json as Moment;
    })(), `POST /moments/${momentId}/posts`),
  somedayFromPost: (postId: string) =>
    request<Intent>("POST", `/moments/posts/${postId}/someday`),
  setTimezone: (timezone: string) =>
    request<{ timezone: string }>("POST", "/me/timezone", { timezone }),
  setMemberRole: (circleId: string, userId: string, role: "admin" | "member" | "owner") =>
    request<{ user_id: string; role: string } | { message: string; new_owner_id: string }>(
      "PATCH", `/circles/${circleId}/members/${userId}`, { role },
    ),
  removeMember: (circleId: string, userId: string) =>
    request<unknown>("DELETE", `/circles/${circleId}/members/${userId}`),
  refreshPreview: (intentId: string) =>
    request<{ id: string; link_meta: LinkMeta }>("POST", `/intents/${intentId}/refresh-preview`),
  intent: (id: string) => request<Intent>("GET", `/intents/${id}`),
  createIntent: (
    circleId: string,
    fields: { title: string; url?: string; note?: string; category?: string; tags?: string[] },
  ) => request<Intent>("POST", `/circles/${circleId}/intents`, fields),
  updateIntent: (id: string, fields: Partial<Pick<Intent, "title" | "url" | "note" | "category" | "task_status" | "planned_for" | "done_note" | "done_photos">> & { tags?: string[] }) =>
    request<Intent>("PATCH", `/intents/${id}`, fields),
  uploadMemoryPhoto: (intentId: string, file: File) =>
    upload<{ url: string }>(`/intents/${intentId}/photos`, file, file.name),
  deleteIntent: (id: string) => request<unknown>("DELETE", `/intents/${id}`),
  react: (id: string) => request<{ reacted: boolean }>("POST", `/intents/${id}/react`),
  boost: (id: string) => request<{ boosted: boolean }>("POST", `/intents/${id}/boost`),

  smartPick: (circleId: string) => request<SmartPick>("GET", `/circles/${circleId}/payoff/smart`),
  spin: (circleId: string) => request<{ shortlist: SpinItem[] }>("GET", `/circles/${circleId}/payoff/spin`),

  unfurl: (url: string) => request<LinkMeta>("POST", "/unfurl", { url }),

  tourSeen: (step_ids: string[]) =>
    request<{ tour_state: TourState }>("POST", "/tour/seen", { step_ids }),
  tourReset: () => request<{ tour_state: TourState }>("POST", "/tour/reset"),

  notifications: () => request<NotificationFeed>("GET", "/notifications"),
  markNotificationsSeen: () => request<{ ok: boolean }>("POST", "/notifications/seen"),

  subscribePush: (sub: { endpoint: string; p256dh: string; auth: string }) =>
    request<{ ok: boolean }>("POST", "/push/subscribe", sub),
  unsubscribePush: (sub: { endpoint: string; p256dh: string; auth: string }) =>
    request<{ ok: boolean }>("DELETE", "/push/subscribe", sub),
};

export { ApiError };
