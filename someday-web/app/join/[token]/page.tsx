"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

export default function JoinPage() {
  const ready = useAuth();
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const ran = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready || ran.current) return;
    ran.current = true;
    api
      .joinCircle(token)
      .then(({ circle_id }) => router.replace(`/circles/${circle_id}`))
      .catch((e) => setError(e instanceof Error ? e.message : "Invalid invite link"));
  }, [ready, token, router]);

  if (!ready) return <Spinner />;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      {error ? (
        <div className="text-center">
          <div className="text-sm" style={{ color: "var(--cp)" }}>{error}</div>
          <button onClick={() => router.replace("/")} className="btn-ghost mt-4 px-6 py-2.5 text-sm">
            Go home
          </button>
        </div>
      ) : (
        <Spinner />
      )}
    </main>
  );
}
