const HTTP_URL = /https?:\/\/[^\s]+/i;

function clean(value, maxLength = 2000) {
  return typeof value === "string" ? value.trim().slice(0, maxLength) : "";
}

function httpUrl(value) {
  const match = clean(value).match(HTTP_URL)?.[0] ?? "";
  if (!match) return "";
  try {
    const parsed = new URL(match);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : "";
  } catch {
    return "";
  }
}

function normalizeWebShare(payload) {
  const text = clean(payload.text);
  const url = httpUrl(payload.url) || httpUrl(text);
  const sharedTitle = clean(payload.title, 120);
  const textWithoutUrl = url ? text.replace(url, "").trim() : text;

  return {
    title: (sharedTitle || textWithoutUrl || text).slice(0, 120),
    text,
    url,
  };
}

module.exports = { normalizeWebShare };
