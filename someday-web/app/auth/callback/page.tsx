"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { Spinner } from "@/components/ui";

export default function AuthCallback() {
  const router = useRouter();
  const ran = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    (async () => {
      // supabase-js parses the #access_token fragment automatically on load;
      // wait for the session to land, then register the user with our API.
      for (let i = 0; i < 20; i++) {
        const { data } = await supabase.auth.getSession();
        if (data.session) {
          try {
            await api.verify();
            const param = new URLSearchParams(location.search).get("next");
            const next =
              (param?.startsWith("/") ? param : null) ?? sessionStorage.getItem("next") ?? "/";
            sessionStorage.removeItem("next");
            router.replace(next);
          } catch {
            setError("Could not complete sign-in. Try again.");
          }
          return;
        }
        await new Promise((r) => setTimeout(r, 250));
      }
      setError("Sign-in link expired or invalid.");
    })();
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      {error ? (
        <div className="text-center">
          <div className="text-sm" style={{ color: "var(--cp)" }}>{error}</div>
          <button onClick={() => router.replace("/login")} className="btn-ghost mt-4 px-6 py-2.5 text-sm">
            Back to login
          </button>
        </div>
      ) : (
        <Spinner />
      )}
    </main>
  );
}
