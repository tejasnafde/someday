# Structured API Error Alerts

## Problem

The API middleware currently reduces every bearer token to its first eight
characters and sends that string as the only user context in Discord alerts.
For authentication failures this produces values such as `token:bogus.jw…`,
while the useful JWT verification error and response detail are discarded.
Discord is displaying the payload exactly as the API sends it.

Raw bearer tokens must not be sent to Discord because they are reusable
credentials. The alert should instead contain enough sanitized evidence to
identify the failure, correlate repeated requests, and distinguish native and
web clients.

## Design

Introduce one structured request-error pipeline for every API 4xx and 5xx
response. A low-level ASGI middleware will observe the response messages as
they are emitted, retaining only a bounded copy of error response bodies. It
will not consume, rebuild, or otherwise change the response delivered to the
client. The middleware will emit at most one Discord alert per failed request.

JWT verification will attach sanitized authentication context to the request:

- On success: verified user ID and email, when present.
- On failure: a stable SHA-256 token fingerprint, token length and segment
  count, safe unverified claims such as subject and expiry when parseable, and
  a classified failure reason such as expired, malformed, invalid signature,
  unknown signing key, or JWKS failure.

The native and web API clients will identify themselves with a small
`X-Someday-Client` header. The native value includes the configured app
version. Browser user-agent information remains available as a fallback.

The Discord formatter remains responsible only for producing and delivering a
valid embed. Alerts will include:

- environment, status, method, and route;
- response error message;
- request duration and Cloud Run trace/request identifier when available;
- client type/version and a bounded user-agent value;
- verified user context or sanitized authentication diagnostics;
- a bounded traceback for unhandled server errors.

All attacker-controlled strings will be neutralized for Discord mentions and
bounded to Discord's embed limits. Authorization headers, cookies, request
bodies, raw tokens, and sensitive query parameters will never be included.
Webhook responses will be checked so rejected Discord payloads are logged.

## Alternatives Considered

Capturing bodies in the existing function middleware would be a smaller diff,
but Starlette may expose streaming responses whose bodies cannot safely be
read and replayed there. Adding alerts separately to every handler would give
precise local context but would be repetitive and easy to omit. A structured
ASGI observer plus request-scoped authentication context provides complete,
centralized evidence without changing API behavior.

## Error Handling

Alert creation and delivery remain best-effort and may never break an API
request. Invalid JSON, oversized values, missing request metadata, malformed
JWTs, Discord timeouts, and Discord non-success responses are handled locally
and logged. A failed alert must not recursively generate another alert.

## Verification

Tests will cover response pass-through and one-alert behavior for representative
401, 404, 422, and 500 responses; exact authentication classifications;
fingerprint correlation; secret redaction; malformed and oversized input;
Discord field limits; webhook rejection logging; client identification; and
the absence of duplicate alerts. The complete API and affected client test
suites will run before deployment. The final diff will also receive an
adversarial Claude Code review, with confirmed findings fixed and retested.
