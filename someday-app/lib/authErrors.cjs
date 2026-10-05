// User-facing copy for sign-in failures. The screen shows only these strings;
// the raw error goes to api.clientError() so Discord still has the detail.

const APPLE_NO_ACCOUNT =
  "Sign in with Apple did not work on this iPhone. Check that you are signed in to your Apple Account in Settings, then try again, or continue with Google.";
const APPLE_FAILED = "Sign in with Apple did not work. Try again, or continue with Google.";
const GOOGLE_FAILED = "Google sign-in did not work. Try again, or use your email.";
const EMAIL_RATE_LIMITED = "Too many emails right now. Wait a minute, then try again.";
const EMAIL_FAILED = "We could not send the code. Try again, or continue with Google.";
const CODE_FAILED = "That code did not work. Check it and try again, or send a new one.";

// The stable code of an SDK error, for logs. Never the message: Supabase
// messages can repeat the email address back.
function errorCode(e) {
  if (!e || typeof e !== "object") return "unknown";
  const parts = [e.code, e.name, e.status].filter((p) => p !== undefined && p !== null && p !== "");
  return parts.length ? parts.join(" ") : "unknown";
}

// null means the user closed the Apple sheet: show nothing, log nothing.
// ERR_REQUEST_UNKNOWN is ASAuthorizationError 1000, usually an iPhone that is
// not signed in to an Apple Account.
function appleSignInMessage(code) {
  if (code === "ERR_REQUEST_CANCELED") return null;
  if (code === "ERR_REQUEST_UNKNOWN") return APPLE_NO_ACCOUNT;
  return APPLE_FAILED;
}

// Same answer for every address, so the screen never says whether an
// account exists. Only the rate limit gets its own copy.
function emailSendMessage(e) {
  const rateLimited =
    e?.status === 429 || /rate.?limit/i.test(String(e?.code ?? "")) || /rate limit/i.test(String(e?.message ?? ""));
  return rateLimited ? EMAIL_RATE_LIMITED : EMAIL_FAILED;
}

// The OAuth redirect URL (someday:?code=... or someday:?error=...).
// access_denied means the user declined on Google's screen: a cancel.
function oauthRedirectResult(url) {
  const code = url.match(/[?&#]code=([\w-]+)/)?.[1];
  if (code) return { code };
  const error = url.match(/[?&#]error=([\w-]+)/)?.[1] ?? "no_code";
  return { error, cancelled: error === "access_denied" };
}

module.exports = {
  GOOGLE_FAILED,
  CODE_FAILED,
  errorCode,
  appleSignInMessage,
  emailSendMessage,
  oauthRedirectResult,
};
