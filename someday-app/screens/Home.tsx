import Constants from "expo-constants";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, BackHandler, Linking, View } from "react-native";
import { WebView } from "react-native-webview";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { useTheme } from "../lib/theme";

const extra = Constants.expoConfig?.extra as Record<string, string>;
const WEB_URL = extra.webUrl;
const API_URL = extra.apiUrl;

// Supabase's implicit-grant URL parser REQUIRES expires_in; without it the web
// client throws "No session defined in URL" and never establishes the session.
// Derive the exact remaining lifetime from the JWT's `exp` claim.
function expiresInFromJwt(accessToken: string): number {
  try {
    const payload = accessToken.split(".")[1];
    const json = JSON.parse(
      decodeURIComponent(
        atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join(""),
      ),
    );
    const remaining = Number(payload && json.exp) - Math.floor(Date.now() / 1000);
    if (Number.isFinite(remaining) && remaining > 0) return remaining;
  } catch {
    // fall through to the standard 1-hour default
  }
  return 3600;
}

export function Home({ nextPath }: { nextPath?: string | null }) {
  const t = useTheme();
  const [startUrl, setStartUrl] = useState<string | null>(null);
  const webRef = useRef<WebView>(null);
  const canGoBack = useRef(false);

  useEffect(() => {
    // Android back gesture navigates WebView history instead of closing the app
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (canGoBack.current) {
        webRef.current?.goBack();
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    // The WebView gets its OWN session from the API - sharing the native
    // session's refresh token would get both revoked by rotation reuse-detection.
    (async () => {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        setStartUrl(WEB_URL + (nextPath ?? ""));
        return;
      }
      try {
        const res = await fetch(`${API_URL}/auth/webview-session`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`webview-session ${res.status}`);
        const s = await res.json();
        const expiresIn = expiresInFromJwt(s.access_token);
        const nextQ = nextPath ? `?next=${encodeURIComponent(nextPath)}` : "";
        setStartUrl(
          `${WEB_URL}/auth/callback${nextQ}#access_token=${s.access_token}&refresh_token=${s.refresh_token}&expires_in=${expiresIn}&token_type=bearer&type=magiclink`,
        );
      } catch (e: unknown) {
        // Bridge failed - fall back to the web app, which may already hold its
        // own session in WebView storage; otherwise it shows its own login.
        api.clientError("webview_session", e instanceof Error ? e.message : String(e));
        setStartUrl(WEB_URL + (nextPath ?? ""));
      }
    })();
  }, [nextPath]);

  if (!startUrl) {
    return (
      <View style={{ flex: 1, justifyContent: "center", backgroundColor: t.bg }}>
        <ActivityIndicator color={t.acc} />
      </View>
    );
  }

  return (
    <WebView
      ref={webRef}
      onNavigationStateChange={(nav) => { canGoBack.current = nav.canGoBack; }}
      source={{ uri: startUrl }}
      style={{ flex: 1, backgroundColor: t.bg }}
      onShouldStartLoadWithRequest={(req) => {
        if (req.url.includes("accounts.google.com")) {
          Linking.openURL(req.url);
          return false;
        }
        return true;
      }}
      domStorageEnabled
      sharedCookiesEnabled
      startInLoadingState
      renderLoading={() => (
        <View style={{ flex: 1, justifyContent: "center", backgroundColor: t.bg }}>
          <ActivityIndicator color={t.acc} />
        </View>
      )}
    />
  );
}
