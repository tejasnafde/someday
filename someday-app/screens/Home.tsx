import Constants from "expo-constants";
import { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { WebView } from "react-native-webview";
import { supabase } from "../lib/supabase";
import { useTheme } from "../lib/theme";

const WEB_URL = (Constants.expoConfig?.extra as Record<string, string>).webUrl;

export function Home() {
  const t = useTheme();
  const [startUrl, setStartUrl] = useState<string | null>(null);

  useEffect(() => {
    // Hand the native session to the web app via the auth callback fragment —
    // supabase-js on the web consumes it and stores its own session.
    supabase.auth.getSession().then(({ data }) => {
      const s = data.session;
      setStartUrl(
        s
          ? `${WEB_URL}/auth/callback#access_token=${s.access_token}&refresh_token=${s.refresh_token}&token_type=bearer&type=magiclink`
          : WEB_URL,
      );
    });
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
