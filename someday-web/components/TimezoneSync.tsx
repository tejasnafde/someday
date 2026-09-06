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
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) return;
      api.setTimezone(tz)
        .then(() => localStorage.setItem("tz-synced", tz))
        .catch(() => {}); // retried on next load
    });
  }, []);
  return null;
}
