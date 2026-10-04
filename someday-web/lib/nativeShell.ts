// Every native shell (Android today, any future iOS shell) appends this mark to
// its WebView user agent via applicationNameForUserAgent in someday-app/screens/Home.tsx.
const SHELL_MARK = /SomedayNative\//;

// True inside a store-installed app. Call only after mount: there is no
// navigator during the server render.
export function isNativeShell(): boolean {
  return SHELL_MARK.test(navigator.userAgent);
}

// The Android app is a native shell around this web app, holding its OWN
// Supabase session (docs/auth-architecture.md). Signing out here only clears
// the WebView session, so tell the shell to drop the native one too.
// window.ReactNativeWebView exists only when the shell registers onMessage;
// in a browser, or a shell without the listener, this does nothing.
export function notifyShellSignedOut(): void {
  shellBridge()?.postMessage(JSON.stringify({ type: "signed-out" }));
}

// The shell keeps its native splash up until this arrives (shells from 1.19.0),
// so a cold launch shows one loading surface. components/ShellReady.tsx sends
// it once the first real screen, not a Spinner or Skeleton, has rendered.
export function notifyShellReady(): void {
  shellBridge()?.postMessage(JSON.stringify({ type: "ready" }));
}

// iPad WebViews send a desktop "Macintosh" user agent; with the shell mark that
// still means the iOS app, because no Mac shell exists.
export function isIosShell(): boolean {
  return isNativeShell() && /iPhone|iPad|iPod|Macintosh/.test(navigator.userAgent);
}

export class AppleReauthCancelled extends Error {
  constructor() {
    super("Confirm with Apple to delete your account.");
  }
}

// Account deletion for an Apple sign-in: the iOS shell re-runs the Apple sheet
// and answers with a fresh authorizationCode, which the API uses to revoke the
// user's Apple tokens (docs/auth-architecture.md). Resolves null when the shell
// cannot get a code, or never answers (shells before this change), so deletion
// still goes ahead. Rejects with AppleReauthCancelled if the user cancels.
export function requestAppleReauth(timeoutMs = 90_000): Promise<string | null> {
  const bridge = shellBridge();
  if (!bridge) return Promise.resolve(null);
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => finish(null), timeoutMs);
    function onReply(e: Event) {
      const detail = (e as CustomEvent<{ type?: string; code?: string | null; cancelled?: boolean }>).detail;
      if (detail?.type !== "apple-reauth") return;
      if (detail.cancelled) finish(new AppleReauthCancelled());
      else finish(detail.code ?? null);
    }
    function finish(result: string | null | Error) {
      clearTimeout(timer);
      window.removeEventListener("someday-shell", onReply);
      if (result instanceof Error) reject(result);
      else resolve(result);
    }
    window.addEventListener("someday-shell", onReply);
    bridge.postMessage(JSON.stringify({ type: "apple-reauth" }));
  });
}

export function shellBridge(): { postMessage: (m: string) => void } | undefined {
  return (window as { ReactNativeWebView?: { postMessage: (m: string) => void } }).ReactNativeWebView;
}
