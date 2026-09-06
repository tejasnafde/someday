import type { Metadata } from "next";
import { DM_Sans, Lora } from "next/font/google";
import { PushInit } from "@/components/PushInit";
import { TimezoneSync } from "@/components/TimezoneSync";
import { Sprite } from "@/components/Sprite";
import "./globals.css";

const dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-dm-sans" });
const lora = Lora({ subsets: ["latin"], variable: "--font-lora" });

export const metadata: Metadata = {
  metadataBase: new URL("https://someday.tn07.dev"),
  title: "Someday",
  description: "For all the things you'll do together someday.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "Someday",
    description: "For all the things you'll do together someday.",
    url: "/",
    siteName: "Someday",
    type: "website",
    images: ["/icon-512.png"],
  },
  twitter: {
    card: "summary",
    title: "Someday",
    description: "For all the things you'll do together someday.",
    images: ["/icon-512.png"],
  },
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Someday",
  },
};

const themeInit = `(function(){var t=localStorage.getItem("theme");if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))document.documentElement.setAttribute("data-theme","dark")})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <script
          defer
          src="https://static.cloudflareinsights.com/beacon.min.js"
          data-cf-beacon='{"token":"4941fd7227a9490b82767bf29eb1b30b"}'
        ></script>
      </head>
      <body className={`${dmSans.variable} ${lora.variable}`} suppressHydrationWarning>
        <Sprite />
        <PushInit />
        <TimezoneSync />
        <div className="orb orb1" />
        <div className="orb orb2" />
        <div className="orb orb3" />
        <div className="relative z-10 mx-auto min-h-screen max-w-md px-5 pb-16">{children}</div>
      </body>
    </html>
  );
}
