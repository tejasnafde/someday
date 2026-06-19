# Auth Architecture

> **Read this before touching anything auth-related in the app, web, or backend.**
> Sign-in spans three codebases and two *separate* Supabase sessions. The design
> is deliberate but non-obvious; every gotcha below cost real debugging time.

---

## The one thing to understand first

The mobile app is **not** a normal native app. It is a **native auth shell wrapping a WebView**:

- `someday-app/screens/SignIn.tsx` — a **native** React Native sign-in screen (no Google logo on the button; that's how you tell it apart from the web one).
- `someday-app/screens/Home.tsx` — once signed in, this is just a **`react-native-webview`** pointing at the web app (`someday-web` on Vercel). Everything past login is the web app rendered inside the shell.

Because of this, **there are two independent Supabase sessions on a signed-in device:**

| Session | Lives in | Created by | Storage |
|---|---|---|---|
| **Native** | the RN app | `SignIn.tsx` OAuth / OTP flow | `AsyncStorage` |
| **WebView** | the embedded web app | minted server-side, handed to the WebView | WebView `localStorage` |

They are **separate on purpose.** Supabase rotates refresh tokens and runs
reuse-detection: if the native app and the WebView shared one refresh-token
family, the first token refresh on either side would invalidate the other and
revoke the whole family — signing the user out everywhere. So the backend mints
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
│      '//' — the URL is `someday:?code=` NOT `someday://?code=`       │
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
   result. The auth code is single-use server-side — two parallel exchanges race
   and the loser gets *"invalid flow state, no valid flow state found"*. Guard
   with a `Set` of already-handled codes (see `SignIn.tsx`).

4. **`WebBrowser.maybeCompleteAuthSession()`** must be called at module level.

### Bridge / WebView (`Home.tsx`)

5. **The callback fragment MUST include `expires_in`.** supabase-js's
   implicit-grant parser throws *"No session defined in URL"* if any of
   `access_token | expires_in | refresh_token | token_type` is missing. Derive
   `expires_in` from the JWT's `exp` claim (don't hardcode). Omitting it makes
   `/auth/callback` poll for 5s and then show *"Sign-in link expired or
   invalid."* — which looks like a web bug but originates in the app.

6. **If `/auth/webview-session` fails, `Home.tsx` falls back to loading the bare
   web login** (`WEB_URL + nextPath`). Symptom: the user sees the *web* login
   page (Google logo button) inside the shell after a "successful" native
   sign-in. That means the bridge failed, not the native auth.

### Backend (`someday-api`)

7. **`/auth/webview-session` needs `SUPABASE_SERVICE_ROLE_KEY`.** It calls
   `admin/generate_link`. Returns 500 if the key isn't configured for the env.

8. **It mints a *new* session deliberately** — do not "optimise" it to reuse the
   native session's tokens (see refresh-token rotation note above).

### Web (`someday-web`)

9. **The web Supabase client uses default options** (`lib/supabase.ts`) —
   implicit flow, `detectSessionInUrl: true`. The WebView bridge depends on this.
   If you ever switch the web client to `flowType: 'pkce'`, the implicit
   `#access_token` fragment from the bridge will be rejected and the WebView
   sign-in breaks. Keep them compatible or migrate both sides together.

---

## Observability

There is **no server log for client-side auth failures** — they happen before
any authenticated backend call. Use the fire-and-forget
`api.clientError(context, message, detail?)` helper (app) →
`POST /auth/client-error` (no JWT) → Discord alert. When debugging an auth
issue, instrument each step with `clientError` and read the Discord channel; the
root cause is almost always visible within one sign-in attempt. Strip the
`DEBUG_*` calls once the issue is fixed.

---

## Key files

| Concern | File |
|---|---|
| Native sign-in + OAuth exchange | `someday-app/screens/SignIn.tsx` |
| Native Linking (invite deep-links) | `someday-app/App.tsx` |
| WebView host + session bridge | `someday-app/screens/Home.tsx` |
| RN Supabase client (PKCE) | `someday-app/lib/supabase.ts` |
| Mint WebView session | `someday-api/handler/auth_handler.py` → `webview_session` |
| Client-error → Discord | `someday-api/routers/auth_router.py` → `/auth/client-error` |
| Web callback (consumes fragment) | `someday-web/app/auth/callback/page.tsx` |
| Web Supabase client (implicit) | `someday-web/lib/supabase.ts` |
