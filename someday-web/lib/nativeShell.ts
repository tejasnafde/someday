// The Android app is a native shell around this web app, holding its OWN
// Supabase session (docs/auth-architecture.md). Signing out here only clears
// the WebView session, so tell the shell to drop the native one too.
// window.ReactNativeWebView exists only when the shell registers onMessage;
// in a browser, or a shell without the listener, this does nothing.
export function notifyShellSignedOut(): void {
  const bridge = (window as { ReactNativeWebView?: { postMessage: (m: string) => void } }).ReactNativeWebView;
  bridge?.postMessage(JSON.stringify({ type: "signed-out" }));
}
