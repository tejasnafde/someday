const HTTP_URL = /https?:\/\/[^\s]+/i;

/**
 * Normalize the platform-specific share-intent shape before rendering capture.
 * Shared files are presence signals only; Someday does not retain their data.
 *
 * @param {{
 *   text?: string | null,
 *   webUrl?: string | null,
 *   files?: Array<{ mimeType?: string | null }> | null,
 * }} payload
 */
function normalizeSharePayload(payload) {
  const text = payload.text?.trim() ?? "";
  const url = payload.webUrl?.match(HTTP_URL)?.[0] ?? text.match(HTTP_URL)?.[0] ?? null;
  const hasMedia = (payload.files?.length ?? 0) > 0;

  return {
    url,
    text,
    hasMedia,
    needsLink: hasMedia && !url && !text,
  };
}

module.exports = { normalizeSharePayload };
