import assert from "node:assert/strict";
import test from "node:test";
import { CALLBACK_FAILED, LINK_EXPIRED, callbackError, emailSendMessage, errorCode } from "../lib/authErrors.cjs";

test("no error on the callback URL means a normal sign-in", () => {
  assert.equal(callbackError("?next=/circles", "#access_token=x&expires_in=3600"), null);
});

test("declining on Google's screen goes back to login silently", () => {
  assert.deepEqual(callbackError("?error=access_denied&error_description=denied", ""), {
    code: "access_denied", message: null, cancelled: true,
  });
});

test("an expired email link asks for a new one", () => {
  const r = callbackError("", "#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid");
  assert.equal(r.message, LINK_EXPIRED);
  assert.equal(r.cancelled, false);
});

test("other callback errors show a short message, never the provider text", () => {
  const r = callbackError("?error=server_error&error_description=Unable+to+exchange+external+code", "");
  assert.deepEqual(r, { code: "server_error", message: CALLBACK_FAILED, cancelled: false });
});

test("email send failures never reveal whether an account exists", () => {
  assert.equal(
    emailSendMessage({ status: 422, code: "otp_disabled", message: "Signups not allowed for otp" }),
    emailSendMessage({ status: 500, message: "boom" }),
  );
  assert.match(emailSendMessage({ status: 429, code: "over_email_send_rate_limit" }), /Too many/);
});

test("logged error codes never carry the SDK message", () => {
  assert.equal(
    errorCode({ code: "validation_failed", name: "AuthApiError", status: 400, message: 'Email "a@b.com" is invalid' }),
    "validation_failed AuthApiError 400",
  );
  assert.equal(errorCode("nope"), "unknown");
});
