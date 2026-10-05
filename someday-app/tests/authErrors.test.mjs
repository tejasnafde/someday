import assert from "node:assert/strict";
import test from "node:test";
import {
  appleSignInMessage,
  emailSendMessage,
  errorCode,
  oauthRedirectResult,
} from "../lib/authErrors.cjs";

test("closing the Apple sheet is silent", () => {
  assert.equal(appleSignInMessage("ERR_REQUEST_CANCELED"), null);
});

test("ASAuthorizationError 1000 points at the Apple Account in Settings", () => {
  assert.match(appleSignInMessage("ERR_REQUEST_UNKNOWN"), /signed in to your Apple Account in Settings/);
});

test("other Apple failures get the generic message with a Google route", () => {
  for (const code of ["ERR_REQUEST_FAILED", "ERR_INVALID_RESPONSE", "ERR_REQUEST_NOT_HANDLED", undefined]) {
    assert.equal(appleSignInMessage(code), "Sign in with Apple did not work. Try again, or continue with Google.");
  }
});

test("email send failures never reveal whether an account exists", () => {
  const signupsOff = emailSendMessage({ status: 422, code: "otp_disabled", message: "Signups not allowed for otp" });
  const unknown = emailSendMessage({ status: 500, message: "boom" });
  assert.equal(signupsOff, unknown);
  assert.match(emailSendMessage({ status: 429, message: "email rate limit exceeded" }), /Too many emails/);
});

test("logged error codes never carry the SDK message", () => {
  const e = { code: "validation_failed", name: "AuthApiError", status: 400, message: 'Email address "a@b.com" is invalid' };
  assert.equal(errorCode(e), "validation_failed AuthApiError 400");
  assert.equal(errorCode(null), "unknown");
});

test("OAuth redirects yield a code, a cancel, or an error", () => {
  assert.deepEqual(oauthRedirectResult("someday:?code=abc-123"), { code: "abc-123" });
  assert.equal(oauthRedirectResult("someday:?error=access_denied&error_description=x").cancelled, true);
  assert.deepEqual(oauthRedirectResult("someday://#error=server_error"), { error: "server_error", cancelled: false });
});
