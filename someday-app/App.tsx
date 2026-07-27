import * as Linking from "expo-linking";
import * as Notifications from "expo-notifications";
import { useShareIntent } from "expo-share-intent";
import * as Updates from "expo-updates";
import { useEffect, useState, useRef } from "react";
import { Platform, SafeAreaView, StatusBar, AppState } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { UpdateBanner } from "./components/UpdateBanner";
import { Home } from "./screens/Home";
import { ShareFlow } from "./screens/ShareFlow";
import { SignIn } from "./screens/SignIn";
import { api } from "./lib/api";
import { registerForPush } from "./lib/push";
import { supabase } from "./lib/supabase";
import { useTheme } from "./lib/theme";

// ErrorUtils is a React Native global - not exported by the react-native package.
declare const ErrorUtils: {
  setGlobalHandler: (handler: (error: Error, isFatal?: boolean) => void) => void;
};
ErrorUtils.setGlobalHandler((error, isFatal) => {
  api.clientError("crash", error.message, isFatal ? "fatal" : "non-fatal").catch(() => {});
});

// Show push notifications when the app is in the foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const INACTIVITY_LIMIT_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

export default function App() {
  const t = useTheme();
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntent();
  const appState = useRef(AppState.currentState);
  const [pendingPath, setPendingPath] = useState<string | null>(null);

  useEffect(() => {
    const handle = (url: string | null) => {
      if (!url) return;
      // Invite link: https://someday.tn07.dev/join/TOKEN (any host matches, so
      // old vercel.app links still resolve).
      const inviteMatch = url.match(/https?:\/\/[^/]+(\/join\/[\w-]+)/);
      if (inviteMatch) { setPendingPath(inviteMatch[1]); return; }
      // OAuth callbacks (someday:?code=...) are handled in SignIn.tsx's local
      // Linking listener so that only ONE exchangeCodeForSession call fires.
    };
    Linking.getInitialURL().then((url) => handle(url));
    const sub = Linking.addEventListener("url", (e) => handle(e.url));
    return () => sub.remove();
  }, []);

  useEffect(() => {
    const checkInactivityAndSession = async () => {
      const lastActive = await AsyncStorage.getItem("last_active_timestamp");
      const now = Date.now();

      if (lastActive && now - parseInt(lastActive, 10) > INACTIVITY_LIMIT_MS) {
        await supabase.auth.signOut();
        setSignedIn(false);
      } else {
        const { data } = await supabase.auth.getSession();
        setSignedIn(!!data.session);
        if (data.session) {
          await AsyncStorage.setItem("last_active_timestamp", now.toString());
        }
      }
    };

    checkInactivityAndSession();

    const { data: sub } = supabase.auth.onAuthStateChange(async (_e, session) => {
      setSignedIn(!!session);
      if (session) {
        await AsyncStorage.setItem("last_active_timestamp", Date.now().toString());
      }
    });

    const appStateSub = AppState.addEventListener("change", async (nextAppState) => {
      if (appState.current.match(/inactive|background/) && nextAppState === "active") {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          const lastActive = await AsyncStorage.getItem("last_active_timestamp");
          const now = Date.now();
          if (lastActive && now - parseInt(lastActive, 10) > INACTIVITY_LIMIT_MS) {
            await supabase.auth.signOut();
            setSignedIn(false);
          } else {
            await AsyncStorage.setItem("last_active_timestamp", now.toString());
          }
        }
      }
      appState.current = nextAppState;
    });

    // OTA: fetch any pending update and reload so the fix is live on next open
    // without requiring a second manual restart.
    Updates.checkForUpdateAsync()
      .then((u) => (u.isAvailable ? Updates.fetchUpdateAsync() : null))
      .then((result) => { if (result) Updates.reloadAsync().catch(() => {}); })
      .catch(() => {});

    return () => {
      sub.subscription.unsubscribe();
      appStateSub.remove();
    };
  }, []);

  // Register push token on sign-in; ponytail: null-on-signout skipped - new user overwrites on their sign-in
  useEffect(() => {
    if (!signedIn) return;
    registerForPush().then((token) => {
      if (token) api.setPushToken(token).catch(() => {});
    });
  }, [signedIn]);

  // Route notification taps into the existing nextPath / WebView deep-link plumbing
  useEffect(() => {
    Notifications.getLastNotificationResponseAsync().then((res) => {
      const path = res?.notification.request.content.data?.path as string | undefined;
      if (path) setPendingPath(path);
    });
    const sub = Notifications.addNotificationResponseReceivedListener((res) => {
      const path = res.notification.request.content.data?.path as string | undefined;
      if (path) setPendingPath(path);
    });
    return () => sub.remove();
  }, []);

  const sharedUrl = hasShareIntent
    ? (shareIntent.webUrl ?? shareIntent.text?.match(/https?:\/\/\S+/)?.[0] ?? null)
    : null;
  const sharedText = hasShareIntent ? (shareIntent.text ?? "") : "";

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.bg, paddingTop: Platform.OS === "android" ? StatusBar.currentHeight ?? 0 : 0 }}>
      <StatusBar barStyle="default" />
      {signedIn === null ? null : !signedIn ? (
        <SignIn shareIntent={hasShareIntent} />
      ) : hasShareIntent ? (
        <ShareFlow url={sharedUrl} text={sharedText} onDone={resetShareIntent} />
      ) : (
        <Home nextPath={pendingPath} />
      )}
      <UpdateBanner />
    </SafeAreaView>
  );
}
