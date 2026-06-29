import { useState, useRef, useEffect } from "react";
import { ActivityIndicator, Keyboard, Text, TextInput, TouchableOpacity, View, KeyboardAvoidingView, Platform } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import Constants from "expo-constants";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { useTheme } from "../lib/theme";

WebBrowser.maybeCompleteAuthSession();

export function SignIn({ shareIntent = false }: { shareIntent?: boolean }) {
  const t = useTheme();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [stage, setStage] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // Guard: the auth code is single-use. Both openAuthSessionAsync's success
  // result AND the Linking listener can deliver the same callback URL. Whichever
  // fires first wins; the second is a no-op. Without this, two parallel
  // exchangeCodeForSession calls race and one gets "invalid flow state".
  const handledCodes = useRef<Set<string>>(new Set());
  // Android: openAuthSessionAsync resolves as "dismiss" when Chrome Custom Tab
  // closes, but the Linking listener may still be in flight. We set a 4s fallback
  // to clear the spinner; the ref lets us cancel it if the listener fires first.
  const busyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (busyTimeoutRef.current) clearTimeout(busyTimeoutRef.current);
  }, []);

  async function exchange(url: string) {
    const authCode = url.match(/[?&]code=([\w-]+)/)?.[1];
    if (!authCode || handledCodes.current.has(authCode)) return;
    handledCodes.current.add(authCode);
    if (busyTimeoutRef.current) { clearTimeout(busyTimeoutRef.current); busyTimeoutRef.current = null; }

    const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(authCode);
    if (exchangeError) {
      api.clientError("google_oauth_exchange", exchangeError.message);
      setError("Sign-in failed - please try again.");
    } else {
      api.verify().catch(() => {});
    }
    setBusy(false);
  }

  // Android: Chrome Custom Tab closes on redirect and the callback URL
  // (someday:?code=...) arrives here via the Linking system, NOT through
  // openAuthSessionAsync's return value.
  useEffect(() => {
    const sub = Linking.addEventListener("url", (e) => {
      if (e.url.startsWith("someday:") && e.url.includes("code=")) exchange(e.url);
    });
    return () => sub.remove();
  }, []);

  async function signInWithGoogle() {
    setBusy(true);
    setError("");
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: "someday://", skipBrowserRedirect: true },
    });
    if (error) { setBusy(false); setError(error.message); return; }
    if (data.url) {
      // Pass "someday:" (no //) as the return scheme - Android strips the slashes.
      const result = await WebBrowser.openAuthSessionAsync(data.url, "someday:");
      if (result.type === "success") {
        // iOS returns the redirect URL directly. On Android the Linking listener
        // above usually fires first; the guard makes whichever loses a no-op.
        exchange(result.url);
      } else {
        // type="dismiss"/"cancel": on Android the Linking listener handles the
        // exchange. Set a fallback to clear the spinner if no code arrives.
        busyTimeoutRef.current = setTimeout(() => setBusy(false), 4000);
      }
    } else {
      setBusy(false);
    }
  }

  async function sendCode() {
    Keyboard.dismiss();
    setBusy(true);
    setError("");
    const webUrl = (Constants.expoConfig?.extra as Record<string, string>).webUrl;
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: `${webUrl}/auth/callback` },
    });
    setBusy(false);
    if (error) setError(error.message.includes("rate limit") ? "Too many emails right now - try again in a bit." : error.message);
    else setStage("code");
  }

  async function verifyCode() {
    Keyboard.dismiss();
    setBusy(true);
    setError("");
    let { error } = await supabase.auth.verifyOtp({ email: email.trim(), token: code.trim(), type: "email" });
    
    // Fallback for magiclink or signup types if the project is configured differently
    if (error && error.message.includes("Token has expired or is invalid")) {
      const retry = await supabase.auth.verifyOtp({ email: email.trim(), token: code.trim(), type: "magiclink" });
      if (retry.error) {
        const retry2 = await supabase.auth.verifyOtp({ email: email.trim(), token: code.trim(), type: "signup" });
        error = retry2.error || retry.error;
      } else {
        error = null;
      }
    }

    if (!error) await api.verify().catch(() => {});
    setBusy(false);
    if (error) setError("That code didn't work - check it and try again.");
  }

  const input = {
    backgroundColor: t.card,
    borderColor: t.brd,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    color: t.txt,
  } as const;

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={{ flex: 1, justifyContent: "center", padding: 28, gap: 14 }}>
      <Text style={{ fontSize: 12, letterSpacing: 3, textTransform: "uppercase", color: t.acc, textAlign: "center", fontWeight: "600" }}>
        Someday
      </Text>
      <Text style={{ fontSize: 26, color: t.txt, textAlign: "center", marginBottom: 10 }}>
        {stage === "email"
          ? (shareIntent ? "Sign in to save this" : "Sign in to start saving")
          : "Enter the code we emailed"}
      </Text>

      {stage === "email" && (
        <>
          <TouchableOpacity
            disabled={busy}
            onPress={signInWithGoogle}
            style={{
              flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10,
              backgroundColor: t.card, borderColor: t.brd, borderWidth: 1,
              borderRadius: 14, padding: 15, opacity: busy ? 0.6 : 1,
            }}
          >
            <Text style={{ color: t.txt, fontWeight: "600", fontSize: 15 }}>Continue with Google</Text>
          </TouchableOpacity>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <View style={{ flex: 1, height: 1, backgroundColor: t.brd }} />
            <Text style={{ color: t.txtL, fontSize: 11 }}>or</Text>
            <View style={{ flex: 1, height: 1, backgroundColor: t.brd }} />
          </View>
        </>
      )}

      {stage === "email" ? (
        <TextInput
          style={input}
          placeholder="you@example.com"
          placeholderTextColor={t.txtL}
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
      ) : (
        <TextInput
          style={[input, { textAlign: "center", fontSize: 22, letterSpacing: 6, marginLeft: 6 }]}
          placeholder="12345678"
          placeholderTextColor={t.txtL}
          keyboardType="number-pad"
          maxLength={10}
          value={code}
          onChangeText={setCode}
        />
      )}

      {error ? <Text style={{ color: t.pink, fontSize: 13, textAlign: "center" }}>{error}</Text> : null}

      <TouchableOpacity
        disabled={busy || (stage === "email" ? !email.includes("@") : code.length < 6)}
        onPress={stage === "email" ? sendCode : verifyCode}
        style={{ backgroundColor: t.acc, borderRadius: 14, padding: 16, alignItems: "center", opacity: busy ? 0.6 : 1 }}
      >
        {busy ? <ActivityIndicator color="#fff" /> : (
          <Text style={{ color: "#fff", fontWeight: "700", fontSize: 15 }}>
            {stage === "email" ? "Send code" : "Sign in"}
          </Text>
        )}
      </TouchableOpacity>

      {stage === "code" && (
        <TouchableOpacity onPress={() => setStage("email")}>
          <Text style={{ color: t.txtM, textAlign: "center", fontSize: 13 }}>Different email</Text>
        </TouchableOpacity>
      )}
    </KeyboardAvoidingView>
  );
}
