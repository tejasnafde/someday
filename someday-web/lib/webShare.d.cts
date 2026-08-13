export function normalizeWebShare(payload: {
  title?: unknown;
  text?: unknown;
  url?: unknown;
}): { title: string; text: string; url: string };
