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

export function shellBridge(): { postMessage: (m: string) => void } | undefined {
  return (window as { ReactNativeWebView?: { postMessage: (m: string) => void } }).ReactNativeWebView;
}
