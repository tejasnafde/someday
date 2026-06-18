"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";

function urlB64ToUint8(b64: string): Uint8Array {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export function PushInit() {
  useEffect(() => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;

    (async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) return;

      const reg = await navigator.serviceWorker.register("/sw.js");
      const existing = await reg.pushManager.getSubscription();

      if (existing) {
        const j = existing.toJSON();
        api.subscribePush({ endpoint: j.endpoint!, p256dh: j.keys!.p256dh, auth: j.keys!.auth }).catch(() => {});
        return;
      }

      const perm = await Notification.requestPermission();
      if (perm !== "granted") return;

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlB64ToUint8(process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!) as unknown as ArrayBuffer,
      });
      const j = sub.toJSON();
      api.subscribePush({ endpoint: j.endpoint!, p256dh: j.keys!.p256dh, auth: j.keys!.auth }).catch(() => {});
    })();
  }, []);

  return null;
}
