"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Sprite";
import { EmptyState, NavBar, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { AppNotification } from "@/lib/types";

function reltime(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function NotifRow({ item }: { item: AppNotification }) {
  const inner = (
    <div
      className="glass flex items-center gap-3.5 rounded-[var(--r)] px-4 py-3.5"
      style={{
        boxShadow: "var(--shc)",
        opacity: item.seen ? 0.65 : 1,
      }}>
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
        style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
        <Icon name="bell" size="sm" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm leading-snug" style={{ color: "var(--txt)" }}>{item.body}</div>
        <div className="mt-0.5 text-[11px]" style={{ color: "var(--txt-l)" }}>{reltime(item.created_at)}</div>
      </div>
      {item.intent_id && (
        <span style={{ color: "var(--txt-l)" }}>
          <Icon name="chevron-right" size="sm" />
        </span>
      )}
    </div>
  );

  if (item.intent_id) {
    return <Link href={`/intents/${item.intent_id}`}>{inner}</Link>;
  }
  return inner;
}

export default function NotificationsPage() {
  const ready = useAuth();
  const [items, setItems] = useState<AppNotification[] | null>(null);

  useEffect(() => {
    if (!ready) return;
    api.notifications().then((feed) => {
      setItems(feed.items);
      if (feed.unseen > 0) api.markNotificationsSeen().catch(() => {});
    });
  }, [ready]);

  if (!ready || items === null) return <Spinner />;

  return (
    <main>
      <NavBar title="Notifications" back="/" />
      {items.length === 0 ? (
        <EmptyState message="Nothing yet - activity from your circles shows up here." />
      ) : (
        <div className="flex flex-col gap-2.5">
          {items.map((item) => (
            <NotifRow key={item.id} item={item} />
          ))}
        </div>
      )}
    </main>
  );
}
