"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { CALLBACK_FAILED, LINK_EXPIRED, callbackError, errorCode } from "@/lib/authErrors.cjs";
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
      // A failed or declined sign-in comes back with ?error= / #error=.
      const failure = callbackError(location.search, location.hash);
      if (failure?.cancelled) {
        router.replace("/login");
        return;
      }
      if (failure) {
        api.clientError("auth_callback", failure.code, "step=redirect");
        setError(failure.message ?? CALLBACK_FAILED);
        return;
      }
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
          } catch (err: unknown) {
            api.clientError("auth_callback", errorCode(err), "step=verify");
            setError(CALLBACK_FAILED);
          }
          return;
        }
        await new Promise((r) => setTimeout(r, 250));
      }
      // In the app shell this means the WebView bridge sent no usable session.
      api.clientError("auth_callback", "no_session", "step=session");
      setError(LINK_EXPIRED);
    })();
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      {error ? (
        <div className="text-center">
          <div className="text-sm" style={{ color: "var(--cp)" }}>{error}</div>
          <button onClick={() => router.replace("/login")} className="btn-ghost mt-4 px-6 py-2.5 text-sm">
            Back to sign-in
          </button>
        </div>
      ) : (
        <Spinner />
      )}
    </main>
  );
}
