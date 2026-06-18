import { useEffect, useState } from "react";
import { ActivityIndicator, Image, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { api, type Circle, type LinkMeta } from "../lib/api";
import { useTheme } from "../lib/theme";

export function ShareFlow({ url, text, onDone }: { url: string | null; text: string; onDone: () => void }) {
  const t = useTheme();
  const [circles, setCircles] = useState<Circle[] | null>(null);
  const [meta, setMeta] = useState<LinkMeta | null>(null);
  const textTitle = url ? text.replace(url, "").trim().slice(0, 120) : text.slice(0, 120);
  const [title, setTitle] = useState(url ? textTitle : textTitle);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.circles().then((c) => {
      setCircles(c);
      if (c.length === 1) setSelected([c[0].id]);
    }).catch((e) => setError(e.message));
    if (url) {
      api.unfurl(url).then((m) => {
        setMeta(m);
        // Prefer a real unfurl title over share-sheet text, but never over user edits
        if (m.title) setTitle((prev) => (!prev || prev === textTitle ? m.title! : prev));
      }).catch(() => {});
    }
  }, [url]);

  async function save() {
    if (!selected.length || !title.trim()) return;
    setBusy(true);
    setError("");
    try {
      // ponytail: serial fan-out (N=circles per share, usually 1–3). Parallel via Promise.all if it ever stings.
      for (const cid of selected) {
        await api.createIntent(cid, { title: title.trim(), url: url ?? undefined });
      }
      onDone(); // clears native intent immediately — prevents Android AppState re-trigger loop
      setSaved(true);
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
        circles.map((c) => {
          const on = selected.includes(c.id);
          return (
            <TouchableOpacity
              key={c.id}
              onPress={() => setSelected((s) => on ? s.filter((x) => x !== c.id) : [...s, c.id])}
              style={{
                backgroundColor: on ? t.accL : t.card,
                borderColor: on ? t.acc : t.brd,
                borderWidth: 1.5,
                borderRadius: 14,
                padding: 15,
                flexDirection: "row",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <View style={{ flexDirection: "row", alignItems: "center", gap: 12, flex: 1 }}>
                <View style={{
                  width: 22, height: 22, borderRadius: 6,
                  borderWidth: 2, borderColor: on ? t.acc : t.brd,
                  backgroundColor: on ? t.acc : "transparent",
                  alignItems: "center", justifyContent: "center",
                }}>
                  {on && <Text style={{ color: "#fff", fontSize: 14, fontWeight: "900", lineHeight: 16 }}>✓</Text>}
                </View>
                <Text style={{ color: t.txt, fontSize: 15, fontWeight: "600", flex: 1 }} numberOfLines={1}>{c.name}</Text>
              </View>
              <Text style={{ color: t.txtM, fontSize: 12 }}>
                {c.member_count} {c.member_count === 1 ? "member" : "members"}
              </Text>
            </TouchableOpacity>
          );
        })
      )}

      {error ? <Text style={{ color: t.pink, fontSize: 13 }}>{error}</Text> : null}

      <TouchableOpacity
        disabled={busy || !selected.length || !title.trim()}
        onPress={save}
        style={{
          backgroundColor: t.acc,
          borderRadius: 14,
          padding: 16,
          alignItems: "center",
          opacity: busy || !selected.length || !title.trim() ? 0.5 : 1,
        }}
      >
        {busy ? <ActivityIndicator color="#fff" /> : (
          <Text style={{ color: "#fff", fontWeight: "700", fontSize: 15 }}>
            {selected.length > 1 ? `Save to ${selected.length} circles` : "Save to Circle"}
          </Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity onPress={onDone} style={{ alignItems: "center", padding: 6 }}>
        <Text style={{ color: t.txtM, fontSize: 13 }}>Cancel</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
