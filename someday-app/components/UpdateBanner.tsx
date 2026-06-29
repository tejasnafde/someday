import { useEffect, useState } from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";
import { checkForApkUpdate, downloadAndInstall, type ApkUpdate } from "../lib/selfUpdate";
import { useTheme } from "../lib/theme";

export function UpdateBanner() {
  const t = useTheme();
  const [update, setUpdate] = useState<ApkUpdate | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    checkForApkUpdate().then(setUpdate);
  }, []);

  if (!update) return null;

  async function install() {
    setBusy(true);
    setError("");
    try {
      await downloadAndInstall(update!);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed - try again");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View
      style={{
        position: "absolute",
        bottom: 24,
        left: 16,
        right: 16,
        backgroundColor: t.card,
        borderColor: t.brd,
        borderWidth: 1,
        borderRadius: 16,
        padding: 14,
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
        shadowColor: "#000",
        shadowOpacity: 0.25,
        shadowRadius: 12,
        elevation: 8,
      }}
    >
      <View style={{ flex: 1 }}>
        <Text style={{ color: t.txt, fontWeight: "700", fontSize: 14 }}>
          Someday {update.version} is ready
        </Text>
        <Text style={{ color: error ? t.pink : t.txtM, fontSize: 12, marginTop: 1 }}>
          {busy ? "Downloading…" : error || "Quick install, no link needed."}
        </Text>
      </View>
      <TouchableOpacity
        disabled={busy}
        onPress={install}
        style={{ backgroundColor: t.acc, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 16 }}
      >
        {busy ? <ActivityIndicator color="#fff" size="small" /> : (
          <Text style={{ color: "#fff", fontWeight: "700", fontSize: 13 }}>Install</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}
