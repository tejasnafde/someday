"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { NavBar, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { CircleDetail } from "@/lib/types";

export default function InvitePage() {
  const ready = useAuth();
  const { id } = useParams<{ id: string }>();
  const [circle, setCircle] = useState<CircleDetail | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (ready) api.circle(id).then(setCircle);
  }, [ready, id]);

  if (!ready || !circle) return <Spinner />;

  const link = `${location.origin}/join/${circle.invite_token}`;

  async function copy() {
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <main>
      <NavBar title="Invite" back={`/circles/${id}`} />

      <div className="py-6 text-center">
        <h1 className="font-serif text-2xl font-medium">
          Bring someone into<br /><em style={{ color: "var(--acc)" }}>{circle.name}</em>
        </h1>
        <p className="mt-2 text-[13px]" style={{ color: "var(--txt-m)" }}>
          Anyone with this link can join the circle.
        </p>
      </div>

      <div className="glass rounded-[var(--r)] p-4" style={{ boxShadow: "var(--shc)" }}>
        <div className="break-all rounded-[var(--rs)] px-3 py-2.5 text-xs"
          style={{ background: "var(--glass-lo)", color: "var(--txt-m)", border: "1px solid var(--brd-s)" }}>
          {link}
        </div>
        <button onClick={copy} className="btn-primary mt-3 w-full py-3 text-sm">
          <Icon name="copy" size="sm" />
          {copied ? "Copied!" : "Copy link"}
        </button>
      </div>
    </main>
  );
}
