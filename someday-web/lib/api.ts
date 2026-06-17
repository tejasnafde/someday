import { supabase } from "./supabase";
import type { Circle, CircleDetail, Intent, LinkMeta, SmartPick, SpinItem, TourState, User } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function upload<T>(path: string, blob: Blob, filename: string): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError(401, "Not signed in");
  const form = new FormData();
  form.append("file", blob, filename);
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, json.message ?? json.detail ?? res.statusText);
  return json as T;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError(401, "Not signed in");

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, json.message ?? json.detail ?? res.statusText);
  return json as T;
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
  updateCircle: (id: string, fields: { name?: string; emoji?: string }) =>
    request<Circle>("PATCH", `/circles/${id}`, fields),
  deleteCircle: (id: string) => request<unknown>("DELETE", `/circles/${id}`),
  joinCircle: (token: string) =>
    request<{ message: string; circle_id: string; name: string }>("POST", `/circles/join/${token}`),
  leaveCircle: (id: string) => request<unknown>("POST", `/circles/${id}/leave`),

  intents: (circleId: string, params?: { task_status?: string; category?: string; tag?: string; shortlist?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.task_status) q.set("task_status", params.task_status);
    if (params?.category) q.set("category", params.category);
    if (params?.tag) q.set("tag", params.tag);
    if (params?.shortlist) q.set("shortlist", "true");
    const qs = q.toString();
    return request<Intent[]>("GET", `/circles/${circleId}/intents${qs ? `?${qs}` : ""}`);
  },
  circleTags: (circleId: string) => request<string[]>("GET", `/circles/${circleId}/tags`),
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
};

export { ApiError };
