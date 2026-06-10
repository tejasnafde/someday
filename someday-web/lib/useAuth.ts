"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "./supabase";

export function useAuth() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        sessionStorage.setItem("next", location.pathname);
        router.replace("/login");
      } else {
        setReady(true);
      }
    });
  }, [router]);

  return ready;
}
