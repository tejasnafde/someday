import type { Metadata } from "next";
import { DM_Sans, Lora } from "next/font/google";
import { Sprite } from "@/components/Sprite";
import "./globals.css";

const dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-dm-sans" });
const lora = Lora({ subsets: ["latin"], variable: "--font-lora" });

export const metadata: Metadata = {
  title: "Someday",
  description: "For all the things you'll do together someday.",
};

const themeInit = `(function(){var t=localStorage.getItem("theme");if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))document.documentElement.setAttribute("data-theme","dark")})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className={`${dmSans.variable} ${lora.variable}`}>
        <Sprite />
        <div className="orb orb1" />
        <div className="orb orb2" />
        <div className="orb orb3" />
        <div className="relative z-10 mx-auto min-h-screen max-w-md px-5 pb-16">{children}</div>
      </body>
    </html>
  );
}
