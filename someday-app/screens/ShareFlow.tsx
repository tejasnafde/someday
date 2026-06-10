import { useEffect, useState } from "react";
import { ActivityIndicator, Image, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { api, type Circle, type LinkMeta } from "../lib/api";
import { useTheme } from "../lib/theme";

export function ShareFlow({ url, text, onDone }: { url: string | null; text: string; onDone: () => void }) {
  const t = useTheme();
  const [circles, setCircles] = useState<Circle[] | null>(null);
  const [meta, setMeta] = useState<LinkMeta | null>(null);
  const [title, setTitle] = useState(url ? "" : text.slice(0, 120));
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.circles().then((c) => {
      setCircles(c);
      if (c.length === 1) setSelected(c[0].id);
    }).catch((e) => setError(e.message));
    if (url) {
      api.unfurl(url).then((m) => {
        setMeta(m);
        if (m.title) setTitle((prev) => prev || m.title!);
      }).catch(() => {});
    }
  }, [url]);

  async function save() {
    if (!selected || !title.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api.createIntent(selected, { title: title.trim(), url: url ?? undefined });
      setSaved(true);
      setTimeout(onDone, 1200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
      setBusy(false);
    }
  }

  if (saved) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", gap: 10 }}>
        <Text style={{ fontSize: 40 }}>✓</Text>
        <Text style={{ fontSize: 18, color: t.txt, fontWeight: "600" }}>Saved for someday</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 22, gap: 16 }}>
      <Text style={{ fontSize: 22, color: t.txt, fontWeight: "600" }}>Save to circle</Text>

      {(meta?.image || meta?.title) && (
        <View style={{ backgroundColor: t.card, borderRadius: 16, overflow: "hidden", borderWidth: 1, borderColor: t.brd }}>
          {meta.image && <Image source={{ uri: meta.image }} style={{ width: "100%", height: 140 }} resizeMode="cover" />}
          <View style={{ padding: 12 }}>
            {meta.site && (
              <Text style={{ fontSize: 10, color: t.txtL, textTransform: "uppercase", letterSpacing: 1 }}>{meta.site}</Text>
            )}
            {meta.title && <Text style={{ fontSize: 14, color: t.txt, fontWeight: "600", marginTop: 2 }}>{meta.title}</Text>}
          </View>
        </View>
      )}

      <TextInput
        style={{ backgroundColor: t.card, borderColor: t.brd, borderWidth: 1, borderRadius: 12, padding: 13, fontSize: 15, color: t.txt }}
        placeholder="What's the plan?"
        placeholderTextColor={t.txtL}
        value={title}
        onChangeText={setTitle}
      />

      <Text style={{ fontSize: 11, color: t.txtL, textTransform: "uppercase", letterSpacing: 1, fontWeight: "600" }}>
        Which circle?
      </Text>

      {!circles ? (
        <ActivityIndicator color={t.acc} />
      ) : circles.length === 0 ? (
        <Text style={{ color: t.txtM, fontSize: 14 }}>
          No circles yet — create one on the web app first.
        </Text>
      ) : (
        circles.map((c) => (
          <TouchableOpacity
            key={c.id}
            onPress={() => setSelected(c.id)}
            style={{
              backgroundColor: selected === c.id ? t.accL : t.card,
              borderColor: selected === c.id ? t.acc : t.brd,
              borderWidth: 1.5,
              borderRadius: 14,
              padding: 15,
              flexDirection: "row",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Text style={{ color: t.txt, fontSize: 15, fontWeight: "600" }}>{c.name}</Text>
            <Text style={{ color: t.txtM, fontSize: 12 }}>
              {c.member_count} {c.member_count === 1 ? "member" : "members"}
            </Text>
          </TouchableOpacity>
        ))
      )}

      {error ? <Text style={{ color: t.pink, fontSize: 13 }}>{error}</Text> : null}

      <TouchableOpacity
        disabled={busy || !selected || !title.trim()}
        onPress={save}
        style={{
          backgroundColor: t.acc,
          borderRadius: 14,
          padding: 16,
          alignItems: "center",
          opacity: busy || !selected || !title.trim() ? 0.5 : 1,
        }}
      >
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={{ color: "#fff", fontWeight: "700", fontSize: 15 }}>Save to Circle</Text>}
      </TouchableOpacity>

      <TouchableOpacity onPress={onDone} style={{ alignItems: "center", padding: 6 }}>
        <Text style={{ color: t.txtM, fontSize: 13 }}>Cancel</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
