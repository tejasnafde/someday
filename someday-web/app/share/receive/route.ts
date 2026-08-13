import { NextResponse } from "next/server";
import { normalizeWebShare } from "@/lib/webShare.cjs";

export async function POST(request: Request) {
  const form = await request.formData();
  const shared = normalizeWebShare({
    title: form.get("title"),
    text: form.get("text"),
    url: form.get("url"),
  });
  const destination = new URL("/share", request.url);
  if (shared.title) destination.searchParams.set("title", shared.title);
  if (shared.text) destination.searchParams.set("text", shared.text);
  if (shared.url) destination.searchParams.set("url", shared.url);

  return NextResponse.redirect(destination, 303);
}
