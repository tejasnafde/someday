import { ImageResponse } from "next/og";
import { getInvitePreview } from "@/lib/invitePreview";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "An invite to a circle on Someday";

// ImageResponse cannot read CSS variables, so these mirror the light-theme
// tokens in globals.css (--bg-a, --bg-c, --txt, --txt-m, --acc, --acc-m).
const T = { bgA: "#F3EEF9", bgC: "#F9EDF3", txt: "#1C1525", txtM: "#5A4E72", acc: "#5B4B8A", accM: "#8B78C0" };

export default async function Image({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const p = await getInvitePreview(token);
  const kicker = p?.inviter_name ? `${p.inviter_name} invited you to` : "You're invited to";
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: 96,
          background: `linear-gradient(135deg, ${T.bgA}, ${T.bgC})`,
          color: T.txt,
        }}
      >
        <div style={{ fontSize: 40, color: T.txtM }}>{kicker}</div>
        <div style={{ fontSize: 96, fontWeight: 700, marginTop: 12, lineHeight: 1.05 }}>
          {p?.circle_name ?? "a circle"}
        </div>
        <div style={{ display: "flex", marginTop: 56 }}>
          <div
            style={{
              fontSize: 36,
              color: "white",
              padding: "18px 40px",
              borderRadius: 18,
              background: `linear-gradient(135deg, ${T.acc}, ${T.accM})`,
            }}
          >
            Join on Someday
          </div>
        </div>
      </div>
    ),
    size,
  );
}
