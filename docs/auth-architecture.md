# Auth Architecture

> **Read this before touching anything auth-related in the app, web, or backend.**
> Sign-in spans three codebases and two *separate* Supabase sessions. The design
> is deliberate but non-obvious; every gotcha below cost real debugging time.

---

## The one thing to understand first

The mobile app is **not** a normal native app. It is a **native auth shell wrapping a WebView**:

- `someday-app/screens/SignIn.tsx` - a **native** React Native sign-in screen (no Google logo on the button; that's how you tell it apart from the web one).
- `someday-app/screens/Home.tsx` - once signed in, this is just a **`react-native-webview`** pointing at the web app (`someday-web` on Vercel). Everything past login is the web app rendered inside the shell.

Because of this, **there are two independent Supabase sessions on a signed-in device:**

| Session | Lives in | Created by | Storage |
|---|---|---|---|
| **Native** | the RN app | `SignIn.tsx` OAuth / OTP flow | `AsyncStorage` |
| **WebView** | the embedded web app | minted server-side, handed to the WebView | WebView `localStorage` |

They are **separate on purpose.** Supabase rotates refresh tokens and runs
reuse-detection: if the native app and the WebView shared one refresh-token
family, the first token refresh on either side would invalidate the other and
revoke the whole family - signing the user out everywhere. So the backend mints
a *second, independent* session for the WebView.

---

## End-to-end sign-in flow (Google OAuth on Android)

```
┌─ NATIVE (someday-app) ──────────────────────────────────────────────┐
│ 1. SignIn.tsx: supabase.auth.signInWithOAuth({provider:'google',     │
│    redirectTo:'someday://', skipBrowserRedirect:true})               │
│    → PKCE: code_verifier written to AsyncStorage                     │
│      key = sb-<project-ref>-auth-token-code-verifier                 │
│ 2. WebBrowser.openAuthSessionAsync(url, 'someday:')  ← Chrome Tab    │
│ 3. Google → Supabase → redirect to  someday:?code=XXXX               │
│    ⚠ Android delivers this via the Linking system, and STRIPS the    │
│      '//' - the URL is `someday:?code=` NOT `someday://?code=`       │
│ 4. exactly ONE exchangeCodeForSession(code) runs (guarded by a Set)  │
│    → NATIVE session saved to AsyncStorage, onAuthStateChange fires   │
└──────────────────────────────────────────────────────────────────────┘
                              │ setSignedIn(true) → Home mounts
                              ▼
┌─ BRIDGE (Home.tsx → backend → WebView) ─────────────────────────────┐
│ 5. Home.tsx POST /auth/webview-session  (Bearer = native token)      │
│ 6. Backend (auth_handler.webview_session) uses the SERVICE-ROLE key: │
│      admin/generate_link (type=magiclink) → hashed_token             │
│      → /auth/v1/verify  → a brand-new, independent session           │
│    returns { access_token, refresh_token }                           │
│ 7. Home.tsx loads the WebView at:                                    │
│      {WEB_URL}/auth/callback#access_token=…&refresh_token=…           │
│        &expires_in=<from JWT exp>&token_type=bearer&type=magiclink    │
└──────────────────────────────────────────────────────────────────────┘
                              ▼
┌─ WEB (someday-web) ─────────────────────────────────────────────────┐
│ 8. /auth/callback/page.tsx: supabase-js auto-parses the #fragment    │
│    (detectSessionInUrl, default implicit flow), establishes the      │
│    WEBVIEW session, calls api.verify(), routes to `next`.            │
└──────────────────────────────────────────────────────────────────────┘
```

iOS differs only at step 3–4: `ASWebAuthenticationSession` returns the callback
URL directly through `openAuthSessionAsync`'s `success` result instead of the
Linking system. Both paths funnel into the same single guarded exchange.

---

## Hard rules / gotchas (each of these was a real bug)

### Native side (`someday-app`)

1. **`flowType: "pkce"` is mandatory** on the RN Supabase client
   (`lib/supabase.ts`). The SDK defaults to `'implicit'`, which never generates
   a `code_verifier`; `exchangeCodeForSession` then posts an empty verifier and
   Supabase rejects it with *"both auth code and code verifier should be
   non-empty"*.

2. **The redirect scheme is `someday:` not `someday://` on Android.** Android
   strips the `//` from custom-scheme deep links. Match with
   `url.startsWith("someday:")`, and pass `"someday:"` as the
   `openAuthSessionAsync` return-url. Matching `someday://` silently drops the
   callback.

3. **Exchange the auth code exactly once.** On Android the callback URL can
   arrive *both* via the Linking listener *and* via `openAuthSessionAsync`'s
   result. The auth code is single-use server-side - two parallel exchanges race
   and the loser gets *"invalid flow state, no valid flow state found"*. Guard
   with a `Set` of already-handled codes (see `SignIn.tsx`).

4. **`WebBrowser.maybeCompleteAuthSession()`** must be called at module level.

### Bridge / WebView (`Home.tsx`)

5. **The callback fragment MUST include `expires_in`.** supabase-js's
   implicit-grant parser throws *"No session defined in URL"* if any of
   `access_token | expires_in | refresh_token | token_type` is missing. Derive
   `expires_in` from the JWT's `exp` claim (don't hardcode). Omitting it makes
   `/auth/callback` poll for 5s and then show *"Sign-in link expired or
   invalid."* - which looks like a web bug but originates in the app.

6. **Sign-out must clear BOTH sessions.** Web sign-out (Settings, and account
   deletion) only clears the WebView session, so the web app posts
   `{"type":"signed-out"}` through `window.ReactNativeWebView` and `Home.tsx`'s
   `onMessage` (shells from 1.18.0) signs the native session out too, which
   returns the shell to `SignIn`. A shell without the listener keeps its native
   session until the refresh token fails.

7. **The splash stays up until the web app posts `{"type":"ready"}`** (shells
   from 1.19.0). `App.tsx` calls `SplashScreen.preventAutoHideAsync()` at
   module load, so a cold launch shows one loading surface instead of splash,
   native spinner, web spinner and skeleton in turn. `components/ShellReady.tsx`
   (web, mounted in the root layout) posts `ready` once no element with
   `data-loading` (the `Spinner` and `Skeleton` components) is in the DOM.
   `Home.tsx`'s `onMessage` hides the splash on it, origin-checked like
   `signed-out`. Native screens (`SignIn`, `ShareFlow`) hide it as soon as they
   render. A safety timeout hides it after 8 s whatever happens, so a web page
   that never posts `ready` costs 8 s, not a stuck app. Any new page-level
   loading placeholder must carry `data-loading`, or the splash drops early.

8. **If `/auth/webview-session` fails, `Home.tsx` falls back to loading the bare
   web login** (`WEB_URL + nextPath`). Symptom: the user sees the *web* login
   page (Google logo button) inside the shell after a "successful" native
   sign-in. That means the bridge failed, not the native auth.

### Backend (`someday-api`)

9. **`/auth/webview-session` needs `SUPABASE_SERVICE_ROLE_KEY`.** It calls
   `admin/generate_link`. Returns 500 if the key isn't configured for the env.

10. **It mints a *new* session deliberately** - do not "optimise" it to reuse the
   native session's tokens (see refresh-token rotation note above).

### Web (`someday-web`)

11. **The web Supabase client uses default options** (`lib/supabase.ts`) -
   implicit flow, `detectSessionInUrl: true`. The WebView bridge depends on this.
   If you ever switch the web client to `flowType: 'pkce'`, the implicit
   `#access_token` fragment from the bridge will be rejected and the WebView
   sign-in breaks. Keep them compatible or migrate both sides together.

---

## Sign in with Apple (iOS)

App Store guideline 4.8: an app that offers Google sign-in must also offer Sign
in with Apple. So the iOS shell shows Apple's system button above Google.
Android and web do not offer Apple, and must not: there is no native Apple
sheet on Android, and the web flow would need a Services ID.

### The native nonce flow

```
SignIn.tsx (iOS only)
1. rawNonce = Crypto.randomUUID()
2. AppleAuthentication.signInAsync({ scopes: FULL_NAME, EMAIL,
     nonce: SHA-256(rawNonce) })        <- native Apple sheet, no browser
3. supabase.auth.signInWithIdToken({ provider: 'apple',
     token: credential.identityToken, nonce: rawNonce })   <- NATIVE client
   -> NATIVE session saved, onAuthStateChange fires
4. api.verify(), then the name (below)
```

After step 3 the flow is the Google flow from step 5: `Home.tsx` mounts and
bridges the WebView through `POST /auth/webview-session`.

Apple puts the SHA-256 of the nonce in the ID token. Supabase hashes the raw
nonce it gets and compares the two, so a stolen ID token cannot be replayed
without the raw nonce. Pass the HASH to Apple and the RAW value to Supabase.
The other way round fails with a nonce mismatch.

### Why no Services ID or client secret

A Services ID and a signed client secret are only for the web OAuth redirect
flow. The native flow sends Supabase an ID token that Apple issued to the app's
bundle ID, so Supabase only checks the token's `aud`. The Supabase Apple
provider needs `app.someday.capture` in its Client IDs, and nothing else. The
client secret becomes necessary only for token revocation (below).

### The name arrives once

Apple returns `credential.fullName` on the FIRST sign-in only. Later sign-ins
return null, also after a reinstall. `/auth/verify` creates the users row with
the email prefix as the display name, so `SignIn.tsx` sends the Apple name
through `PATCH /auth/me` only when the stored name is empty or still that
prefix. A name the user chose is never overwritten. If that first PATCH fails,
the name is gone; the user can set it in Settings.

### "Hide my email" relay addresses

A user can hide their email. The ID token then carries
`<random>@privaterelay.appleid.com`. The API treats it as a normal email
(`tests/test_apple_relay_email.py`), and the WebView bridge works because
`admin/generate_link` sends no mail. But Apple's relay only delivers mail from
domains registered with Apple (Certificates, Identifiers & Profiles, Services,
Sign in with Apple for Email Communication). Until the Supabase sending domain
is registered there, magic-link and OTP email to a relay address does not
arrive. Such users must keep using Apple to sign in. Follow-up, not done.

### Token revocation on account deletion

Apple requires an app that offers Sign in with Apple to revoke the user's Apple
tokens when the account is deleted. Supabase keeps no Apple refresh token for a
native sign-in, so the iOS shell gets a fresh `authorizationCode` at deletion
time:

```
Settings "Delete account" (web, inside the iOS shell WebView)
1. the session's app_metadata.providers includes "apple" and isIosShell()
2. web posts { type: "apple-reauth" } to the shell        (nativeShell.ts)
3. Home.tsx (iOS only) runs AppleAuthentication.signInAsync()
4. the shell dispatches a "someday-shell" event { type: "apple-reauth",
     code, cancelled } into the page, only if the page is still our origin
5. DELETE /auth/me { apple_authorization_code: code }
6. API, after the DB delete commits: if the verified JWT's
     app_metadata.providers includes "apple"
   -> POST appleid.apple.com/auth/token  (grant_type=authorization_code)
   -> POST appleid.apple.com/auth/revoke (the refresh_token,
        token_type_hint=refresh_token)
```

Both Apple calls send a `client_secret`: an ES256 JWT with `iss` = team ID,
`sub` = `app.someday.capture`, `aud` = `https://appleid.apple.com`, header
`kid` = key ID, and a 5-minute expiry (`account_helper.apple_client_secret`).
The key is the JSON `{key_id, team_id, client_id, p8}` in Secret Manager
`SOMEDAY_SIWA_KEY`. The deploy attaches it as an env var of the same name with
`--set-secrets`, beside `SOMEDAY_CONFIG`.

Rules that keep this safe:

- **Revoke never blocks deletion.** The DB delete is the source of truth. A
  failed exchange or revoke, a missing key, or an Apple user who sent no code
  logs ERROR, and the account is deleted anyway.
- **The server decides who is an Apple user**, from the Supabase-signed JWT,
  not from the client. A code sent for a non-Apple user is ignored.
- **Cancel stops deletion.** If the user cancels the Apple sheet, the web shows
  "Confirm with Apple to delete your account." and deletes nothing.
- **Old shells still delete.** A shell that never answers makes the web wait
  90 seconds and then delete without a code (logged as not revoked).
- Outside the iOS shell, and for non-Apple users, the request has no body and
  the flow is unchanged.

---

## Observability

There is **no server log for client-side auth failures** - they happen before
any authenticated backend call. Use the fire-and-forget
`api.clientError(context, message, detail?)` helper (app) →
`POST /auth/client-error` (no JWT) → Discord alert. When debugging an auth
issue, instrument each step with `clientError` and read the Discord channel; the
root cause is almost always visible within one sign-in attempt. Strip the
`DEBUG_*` calls once the issue is fixed.

Sign-in screens never show SDK text. User copy and the error-code helper live
in `authErrors.cjs` (`someday-app/lib/` and `someday-web/lib/`). Send
`errorCode(e)` plus a `step=` detail to `clientError`, not the SDK message:
Supabase messages can repeat the email back. A cancel (Apple
`ERR_REQUEST_CANCELED`, Google `access_denied`, a closed browser) shows nothing
and logs nothing. Email-code errors read the same for every address. The API
runs client text through `log_util.redact()` (masks emails, blanks `code=`,
`token=` and `nonce=` values) before it logs or alerts.

---

## Key files

| Concern | File |
|---|---|
| Native sign-in + OAuth exchange + Apple (iOS) | `someday-app/screens/SignIn.tsx` |
| Native Linking (invite deep-links) | `someday-app/App.tsx` |
| WebView host + session bridge | `someday-app/screens/Home.tsx` |
| RN Supabase client (PKCE) | `someday-app/lib/supabase.ts` |
| Apple token revoke on deletion | `someday-api/modules/account/account_helper.py` → `revoke_apple_tokens`; shell side `someday-web/lib/nativeShell.ts` → `requestAppleReauth` |
| Mint WebView session | `someday-api/handler/auth_handler.py` → `webview_session` |
| Client-error → Discord | `someday-api/routers/auth_router.py` → `/auth/client-error` |
| Web callback (consumes fragment) | `someday-web/app/auth/callback/page.tsx` |
| Web Supabase client (implicit) | `someday-web/lib/supabase.ts` |
