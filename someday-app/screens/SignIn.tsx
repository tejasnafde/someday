import { useState, useRef, useEffect } from "react";
import { ActivityIndicator, Keyboard, Text, TextInput, TouchableOpacity, View, KeyboardAvoidingView, Platform, useColorScheme } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";
import * as Crypto from "expo-crypto";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import Constants from "expo-constants";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { useTheme } from "../lib/theme";
import { CODE_FAILED, GOOGLE_FAILED, appleSignInMessage, emailSendMessage, errorCode, oauthRedirectResult } from "../lib/authErrors.cjs";

WebBrowser.maybeCompleteAuthSession();

export function SignIn({ shareIntent = false }: { shareIntent?: boolean }) {
  const t = useTheme();
  const scheme = useColorScheme();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [stage, setStage] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // One sign-in attempt at a time. A ref, not the busy state: two taps in the
  // same frame both read busy=false, and the Apple system button cannot be disabled.
  const inFlight = useRef(false);
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

  function begin() {
    if (inFlight.current) return false;
    inFlight.current = true;
    setBusy(true);
    setError("");
    return true;
  }

  function end() {
    inFlight.current = false;
    setBusy(false);
  }

  async function exchange(url: string) {
    const result = oauthRedirectResult(url);
    // Supabase answers ?error= when Google fails or the user declines.
    const key = result.code ?? url;
    if (handledCodes.current.has(key)) return;
    handledCodes.current.add(key);
    if (busyTimeoutRef.current) { clearTimeout(busyTimeoutRef.current); busyTimeoutRef.current = null; }

    try {
      if (!result.code) {
        if (!result.cancelled) {
          api.clientError("google_sign_in", `redirect_error ${result.error}`, "step=redirect");
          setError(GOOGLE_FAILED);
        }
        return;
      }
      const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(result.code);
      if (exchangeError) {
        api.clientError("google_sign_in", errorCode(exchangeError), "step=exchange");
        setError(GOOGLE_FAILED);
      } else {
        api.verify().catch(() => {});
      }
    } catch (e: unknown) {
      api.clientError("google_sign_in", errorCode(e), "step=exchange");
      setError(GOOGLE_FAILED);
    } finally {
      end();
    }
  }

  // Android: Chrome Custom Tab closes on redirect and the callback URL
  // (someday:?code=...) arrives here via the Linking system, NOT through
  // openAuthSessionAsync's return value.
  useEffect(() => {
    const sub = Linking.addEventListener("url", (e) => {
      if (e.url.startsWith("someday:") && /[?&#](code|error)=/.test(e.url)) exchange(e.url);
    });
    return () => sub.remove();
  }, []);

  async function signInWithGoogle() {
    if (!begin()) return;
    try {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: "someday://", skipBrowserRedirect: true },
      });
      if (error || !data.url) {
        api.clientError("google_sign_in", errorCode(error ?? { code: "no_url" }), "step=start");
        setError(GOOGLE_FAILED);
        end();
        return;
      }
      // Pass "someday:" (no //) as the return scheme - Android strips the slashes.
      const result = await WebBrowser.openAuthSessionAsync(data.url, "someday:");
      if (result.type === "success") {
        // iOS returns the redirect URL directly. On Android the Linking listener
        // above usually fires first; the guard makes whichever loses a no-op.
        exchange(result.url);
      } else if (Platform.OS === "ios") {
        // The user closed the browser. iOS has no Linking path, so nothing else is coming.
        end();
      } else {
        // type="dismiss"/"cancel": on Android the Linking listener handles the
        // exchange. Set a fallback to clear the spinner if no code arrives.
        busyTimeoutRef.current = setTimeout(end, 4000);
      }
    } catch (e: unknown) {
      api.clientError("google_sign_in", errorCode(e), "step=browser");
      setError(GOOGLE_FAILED);
      end();
    }
  }

  // Apple sends the name on the FIRST sign-in only. verify() creates the users
  // row with the email prefix as the name, so that prefix (or empty) means the
  // user never chose a name and the Apple name may replace it.
  async function saveAppleName(fullName: string) {
    const { user } = await api.verify();
    if (fullName && (!user.display_name || user.display_name === user.email.split("@")[0])) {
      await api.setDisplayName(fullName);
    }
  }

  // iOS only (App Store guideline 4.8). Native flow: Apple signs an ID token
  // over SHA-256(rawNonce), and Supabase checks it against the raw nonce. No
  // browser, no Services ID, no client secret. See docs/auth-architecture.md.
  async function signInWithApple() {
    if (!begin()) return;
    let step = "apple_sheet";
    try {
      const rawNonce = Crypto.randomUUID();
      const hashedNonce = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, rawNonce);
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
        nonce: hashedNonce,
      });
      step = "supabase_id_token";
      if (!credential.identityToken) throw { code: "no_identity_token" };
      const { error: idTokenError } = await supabase.auth.signInWithIdToken({
        provider: "apple",
        token: credential.identityToken,
        nonce: rawNonce,
      });
      if (idTokenError) throw idTokenError;
      const fullName = [credential.fullName?.givenName, credential.fullName?.familyName]
        .filter(Boolean).join(" ").trim();
      // Signed in now; a failure here must not show a sign-in error.
      saveAppleName(fullName).catch((e: unknown) => api.clientError("apple_name", errorCode(e)));
    } catch (e: unknown) {
      // Only the Apple sheet can be cancelled; a Supabase failure is never a cancel.
      const message = appleSignInMessage(step === "apple_sheet" ? (e as { code?: string })?.code : undefined);
      if (message === null) return; // The user closed the Apple sheet.
      api.clientError("apple_sign_in", errorCode(e), `step=${step}`);
      setError(message);
    } finally {
      end();
    }
  }

  async function sendCode() {
    Keyboard.dismiss();
    if (!begin()) return;
    try {
      const webUrl = (Constants.expoConfig?.extra as Record<string, string>).webUrl;
      const { error } = await supabase.auth.signInWithOtp({
        email: email.trim(),
        options: { emailRedirectTo: `${webUrl}/auth/callback` },
      });
      if (error) throw error;
      setStage("code");
    } catch (e: unknown) {
      api.clientError("email_sign_in", errorCode(e), "step=send_code");
      setError(emailSendMessage(e));
    } finally {
      end();
    }
  }

  async function verifyCode() {
    Keyboard.dismiss();
    if (!begin()) return;
    try {
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
      if (error) throw error;
      await api.verify().catch(() => {});
    } catch (e: unknown) {
      api.clientError("email_sign_in", errorCode(e), "step=verify_code");
      setError(CODE_FAILED);
    } finally {
      end();
    }
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
          {Platform.OS === "ios" && (
            // Apple's HIG requires the system button, so it is exempt from the
            // one-gradient button rule. Same width and radius as Google's.
            <AppleAuthentication.AppleAuthenticationButton
              buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
              buttonStyle={scheme === "dark"
                ? AppleAuthentication.AppleAuthenticationButtonStyle.WHITE
                : AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
              cornerRadius={14}
              onPress={signInWithApple}
              style={{ height: 50, opacity: busy ? 0.6 : 1 }}
            />
          )}
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
        <TouchableOpacity onPress={() => { setStage("email"); setCode(""); setError(""); }}>
          <Text style={{ color: t.txtM, textAlign: "center", fontSize: 13 }}>Change email or resend</Text>
        </TouchableOpacity>
      )}
    </KeyboardAvoidingView>
  );
}
