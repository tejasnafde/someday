"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";

/**
 * Keeps the server-side timezone current so Meanwhile pings land inside the
 * member's real waking hours. Runs once per browser per timezone value -
 * localStorage remembers what was last synced, so travel updates it and
 * ordinary sessions send nothing.
 */
export function TimezoneSync() {
  useEffect(() => {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (!tz || localStorage.getItem("tz-synced") === tz) return;
    // On a first sign-in this runs before /auth/verify has created the account
    // row, so the first call 404s. Retry after the home page has registered the
    // user; anything still failing is retried on the next load.
    const delays = [3000, 10000, 30000];
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;
    function attempt(i: number) {
      timer = setTimeout(() => {
        supabase.auth.getSession().then(({ data }) => {
          if (cancelled || !data.session) return;
          api.setTimezone(tz)
            .then(() => localStorage.setItem("tz-synced", tz))
            .catch(() => { if (!cancelled && i + 1 < delays.length) attempt(i + 1); });
        });
      }, delays[i]);
    }
    attempt(0);
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, []);
  return null;
}
