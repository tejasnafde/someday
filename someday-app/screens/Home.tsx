import Constants from "expo-constants";
import { Linking, Text, TouchableOpacity, View } from "react-native";
import { supabase } from "../lib/supabase";
import { useTheme } from "../lib/theme";

const WEB_URL = (Constants.expoConfig?.extra as Record<string, string>).webUrl;

export function Home() {
  const t = useTheme();

  return (
    <View style={{ flex: 1, justifyContent: "center", padding: 28, gap: 14 }}>
      <Text style={{ fontSize: 12, letterSpacing: 3, textTransform: "uppercase", color: t.acc, textAlign: "center", fontWeight: "600" }}>
        Someday
      </Text>
      <Text style={{ fontSize: 24, color: t.txt, textAlign: "center", lineHeight: 32 }}>
        Share anything from any app{"\n"}to save it for someday.
      </Text>
      <Text style={{ fontSize: 14, color: t.txtM, textAlign: "center", lineHeight: 21 }}>
        Open Instagram, YouTube, or your browser, hit Share, and pick Someday. Everything else lives on the web.
      </Text>

      <TouchableOpacity
        onPress={() => Linking.openURL(WEB_URL)}
        style={{ backgroundColor: t.acc, borderRadius: 14, padding: 16, alignItems: "center", marginTop: 12 }}
      >
        <Text style={{ color: "#fff", fontWeight: "700", fontSize: 15 }}>Open Someday on the web</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => supabase.auth.signOut()} style={{ alignItems: "center", padding: 8 }}>
        <Text style={{ color: t.txtM, fontSize: 13 }}>Sign out</Text>
      </TouchableOpacity>

      <Text style={{ color: t.txtL, fontSize: 11, textAlign: "center" }}>v1.0.1</Text>
    </View>
  );
}
