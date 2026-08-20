import Constants from "expo-constants";
import { supabase } from "./supabase";

const BASE = (Constants.expoConfig?.extra as Record<string, string>).apiUrl;
const CLIENT_HEADERS = {
  "X-Someday-Client": `native/${Constants.expoConfig?.version ?? "unknown"}`,
};

export interface Circle {
  id: string;
  name: string;
  member_count: number;
  open_intent_count: number;
}

export interface LinkMeta {
  title: string | null;
  image: string | null;
  site: string | null;
}

const TIMEOUT_MS = 15000;

// Reject a request that hasn't settled in 15s so a hung fetch or stalled
// getSession() can't leave a caller's loading state stuck forever.
// ponytail: races the whole op; the underlying fetch may run to completion.
function withTimeout<T>(work: Promise<T>, label: string): Promise<T> {
  return Promise.race([
    work,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`${label} timed out`)), TIMEOUT_MS),
    ),
  ]);
}

function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  return withTimeout((async (): Promise<T> => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) throw new Error("Not signed in");

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
    if (!res.ok) throw new Error(json.message ?? json.detail ?? res.statusText);
    return json as T;
  })(), `${method} ${path}`);
}

export const api = {
  verify: () => request("POST", "/auth/verify"),
  clientError: (context: string, message: string, detail?: string) =>
    fetch(`${BASE}/auth/client-error`, {
      method: "POST",
      headers: { ...CLIENT_HEADERS, "Content-Type": "application/json" },
      body: JSON.stringify({ context, message, detail }),
    }).catch(() => {}), // fire-and-forget, never throws
  circles: () => request<Circle[]>("GET", "/circles"),
  unfurl: (url: string) => request<LinkMeta>("POST", "/unfurl", { url }),
  createIntent: (circleId: string, fields: { title: string; url?: string; note?: string }) =>
    request("POST", `/circles/${circleId}/intents`, fields),
  setPushToken: (token: string | null) =>
    request("PATCH", "/auth/me/push-token", { token }),
};
