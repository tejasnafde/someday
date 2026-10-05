// User-facing copy for sign-in failures. The page shows only these strings;
// the raw error goes to api.clientError() so Discord still has the detail.

const GOOGLE_FAILED = "Google sign-in did not work. Try again, or use your email.";
const EMAIL_RATE_LIMITED = "Too many sign-in emails right now. Wait a minute, then try again.";
const EMAIL_FAILED = "We could not send the email. Try again, or continue with Google.";
const CODE_FAILED = "That code did not work. Check it and try again, or send a new one.";
const LINK_EXPIRED = "This sign-in link expired. Go back and send a new one.";
const CALLBACK_FAILED = "Sign-in did not work. Go back and try again.";

// The stable code of an SDK error, for logs. Never the message: Supabase
// messages can repeat the email address back.
function errorCode(e) {
  if (!e || typeof e !== "object") return "unknown";
  const parts = [e.code, e.name, e.status].filter((p) => p !== undefined && p !== null && p !== "");
  return parts.length ? parts.join(" ") : "unknown";
}

// Same answer for every address, so the page never says whether an account
// exists. Only the rate limit gets its own copy.
function emailSendMessage(e) {
  const rateLimited =
    e?.status === 429 || /rate.?limit/i.test(String(e?.code ?? "")) || /rate limit/i.test(String(e?.message ?? ""));
  return rateLimited ? EMAIL_RATE_LIMITED : EMAIL_FAILED;
}

// Supabase puts ?error= (or #error= in the implicit flow) on the callback URL
// when sign-in fails. null means there is no error to handle.
function callbackError(search, hash) {
  const params = new URLSearchParams(search);
  for (const [k, v] of new URLSearchParams(String(hash).replace(/^#/, ""))) params.set(k, v);
  const error = params.get("error");
  if (!error) return null;
  const code = params.get("error_code") ?? "";
  if (code === "otp_expired") return { code, message: LINK_EXPIRED, cancelled: false };
  // The user declined on Google's screen: back to the login page, no error.
  if (error === "access_denied" && !code) return { code: error, message: null, cancelled: true };
  return { code: code || error, message: CALLBACK_FAILED, cancelled: false };
}

module.exports = {
  GOOGLE_FAILED,
  CODE_FAILED,
  LINK_EXPIRED,
  CALLBACK_FAILED,
  errorCode,
  emailSendMessage,
  callbackError,
};
