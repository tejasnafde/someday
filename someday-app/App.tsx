import { useShareIntent } from "expo-share-intent";
import * as Updates from "expo-updates";
import { useEffect, useState } from "react";
import { SafeAreaView, StatusBar } from "react-native";
import { UpdateBanner } from "./components/UpdateBanner";
import { Home } from "./screens/Home";
import { ShareFlow } from "./screens/ShareFlow";
import { SignIn } from "./screens/SignIn";
import { supabase } from "./lib/supabase";
import { useTheme } from "./lib/theme";

export default function App() {
  const t = useTheme();
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntent();

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSignedIn(!!data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => setSignedIn(!!session));

    // OTA: fetch any pending update now; it applies on next launch
    Updates.checkForUpdateAsync()
      .then((u) => (u.isAvailable ? Updates.fetchUpdateAsync() : null))
      .catch(() => {});

    return () => sub.subscription.unsubscribe();
  }, []);

  const sharedUrl = hasShareIntent
    ? (shareIntent.webUrl ?? shareIntent.text?.match(/https?:\/\/\S+/)?.[0] ?? null)
    : null;
  const sharedText = hasShareIntent ? (shareIntent.text ?? "") : "";

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.bg }}>
      <StatusBar barStyle="default" />
      {signedIn === null ? null : !signedIn ? (
        <SignIn />
      ) : hasShareIntent ? (
        <ShareFlow url={sharedUrl} text={sharedText} onDone={resetShareIntent} />
      ) : (
        <Home />
      )}
      <UpdateBanner />
    </SafeAreaView>
  );
}
