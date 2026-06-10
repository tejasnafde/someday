import Constants from "expo-constants";
import { supabase } from "./supabase";

const BASE = (Constants.expoConfig?.extra as Record<string, string>).apiUrl;

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

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Not signed in");

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.message ?? json.detail ?? res.statusText);
  return json as T;
}

export const api = {
  verify: () => request("POST", "/auth/verify"),
  circles: () => request<Circle[]>("GET", "/circles"),
  unfurl: (url: string) => request<LinkMeta>("POST", "/unfurl", { url }),
  createIntent: (circleId: string, fields: { title: string; url?: string; note?: string }) =>
    request("POST", `/circles/${circleId}/intents`, fields),
};
