import type { Metadata } from "next";
import { getInvitePreview, inviteTitle } from "@/lib/invitePreview";
import { JoinClient } from "./JoinClient";

const DESCRIPTION = "Save the plans you keep saying you'll do someday, and actually do them together.";

export async function generateMetadata({ params }: { params: Promise<{ token: string }> }): Promise<Metadata> {
  const { token } = await params;
  const title = inviteTitle(await getInvitePreview(token));
  return {
    title,
    description: DESCRIPTION,
    robots: { index: false },
    alternates: { canonical: null },
    openGraph: { title, description: DESCRIPTION, url: `/join/${token}`, siteName: "Someday", type: "website" },
    twitter: { card: "summary_large_image", title, description: DESCRIPTION },
  };
}

export default function JoinPage() {
  return <JoinClient />;
}
