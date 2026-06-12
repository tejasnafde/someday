import Constants from "expo-constants";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, BackHandler, View } from "react-native";
import { WebView } from "react-native-webview";
import { supabase } from "../lib/supabase";
import { useTheme } from "../lib/theme";

const extra = Constants.expoConfig?.extra as Record<string, string>;
const WEB_URL = extra.webUrl;
const API_URL = extra.apiUrl;

export function Home() {
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
    // The WebView gets its OWN session from the API — sharing the native
    // session's refresh token would get both revoked by rotation reuse-detection.
    (async () => {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        setStartUrl(WEB_URL);
        return;
      }
      try {
        const res = await fetch(`${API_URL}/auth/webview-session`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(String(res.status));
        const s = await res.json();
        setStartUrl(
          `${WEB_URL}/auth/callback#access_token=${s.access_token}&refresh_token=${s.refresh_token}&token_type=bearer&type=magiclink`,
        );
      } catch {
        // Web app may already hold its own session in WebView storage
        setStartUrl(WEB_URL);
      }
    })();
  }, []);

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
