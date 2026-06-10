import { useState } from "react";
import { ActivityIndicator, Text, TextInput, TouchableOpacity, View } from "react-native";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { useTheme } from "../lib/theme";

export function SignIn() {
  const t = useTheme();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [stage, setStage] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function sendCode() {
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.signInWithOtp({ email: email.trim() });
    setBusy(false);
    if (error) setError(error.message.includes("rate limit") ? "Too many emails right now — try again in a bit." : error.message);
    else setStage("code");
  }

  async function verifyCode() {
    setBusy(true);
    setError("");
    const { error } = await supabase.auth.verifyOtp({ email: email.trim(), token: code.trim(), type: "email" });
    if (!error) await api.verify().catch(() => {});
    setBusy(false);
    if (error) setError("That code didn't work — check it and try again.");
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
    <View style={{ flex: 1, justifyContent: "center", padding: 28, gap: 14 }}>
      <Text style={{ fontSize: 12, letterSpacing: 3, textTransform: "uppercase", color: t.acc, textAlign: "center", fontWeight: "600" }}>
        Someday
      </Text>
      <Text style={{ fontSize: 26, color: t.txt, textAlign: "center", marginBottom: 10 }}>
        {stage === "email" ? "Sign in to start saving" : "Enter the code we emailed"}
      </Text>

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
          style={[input, { textAlign: "center", fontSize: 22, letterSpacing: 6 }]}
          placeholder="123456"
          placeholderTextColor={t.txtL}
          keyboardType="number-pad"
          maxLength={6}
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
    </View>
  );
}
