"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Sprite";
import { detectInstallPlatform, type InstallPlatform } from "@/lib/installPlatform.cjs";

const APK_URL = "https://github.com/tejasnafde/someday/releases/latest/download/someday.apk";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallSomeday() {
  const [platform, setPlatform] = useState<InstallPlatform | null>(null);
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);

  useEffect(() => {
    const standalone = window.matchMedia("(display-mode: standalone)").matches
      || Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
    setPlatform(detectInstallPlatform({
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      maxTouchPoints: navigator.maxTouchPoints,
      standalone,
    }));

    function capturePrompt(event: Event) {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    }
    window.addEventListener("beforeinstallprompt", capturePrompt);
    return () => window.removeEventListener("beforeinstallprompt", capturePrompt);
  }, []);

  async function promptInstall() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const result = await installPrompt.userChoice;
    if (result.outcome === "accepted") setPlatform("installed");
    setInstallPrompt(null);
  }

  if (!platform) return null;

  return (
    <section className="glass mt-5 rounded-[var(--r)] p-5" style={{ boxShadow: "var(--shc)" }}>
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--rs)]"
          style={{ background: "var(--acc-l)", color: "var(--acc)" }}>
          <Icon name={platform === "installed" ? "check" : "download"} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="font-serif text-base font-semibold">
            {platform === "installed" ? "Someday is installed" : "Install Someday"}
          </h2>
          <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
            {platform === "android" && "Save reels and links straight from Android's share sheet."}
            {platform === "ios" && "Keep Someday on your Home Screen with its own icon."}
            {platform === "desktop" && "Open Someday like an app from your browser or desktop."}
            {platform === "installed" && "You can launch it from your Home Screen or app launcher."}
          </p>
        </div>
      </div>

      {platform === "android" && (
        <>
          <a href={APK_URL} className="btn-primary mt-4 w-full py-3.5 text-sm">
            <Icon name="download" size="sm" />
            Download latest Android APK
          </a>
          <p className="mt-3 text-center text-[11px] leading-relaxed" style={{ color: "var(--txt-l)" }}>
            The same link always downloads the newest release. Installed APKs also check for updates automatically.
          </p>
        </>
      )}

      {platform === "ios" && (
        <ol className="mt-4 flex flex-col gap-2.5 text-sm">
          <InstallStep number="1" text="Open this page in Safari." />
          <InstallStep number="2" text="Tap Share in Safari's toolbar." />
          <InstallStep number="3" text="Choose Add to Home Screen, then tap Add." />
        </ol>
      )}

      {platform === "desktop" && (
        installPrompt ? (
          <button onClick={promptInstall} className="btn-primary mt-4 w-full py-3.5 text-sm">
            <Icon name="download" size="sm" />
            Install from browser
          </button>
        ) : (
          <p className="mt-4 rounded-[var(--rs)] px-3.5 py-3 text-xs leading-relaxed"
            style={{ background: "var(--glass-lo)", color: "var(--txt-m)" }}>
            In Chrome or Edge, open the browser menu and choose <strong style={{ color: "var(--txt)" }}>Install Someday</strong>.
          </p>
        )
      )}
    </section>
  );
}
function InstallStep({ number, text }: { number: string; text: string }) {
  return (
    <li className="flex items-center gap-3">
      <span className="tnum flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
        style={{ background: "var(--acc-l)", color: "var(--acc)" }}>{number}</span>
      <span style={{ color: "var(--txt-m)" }}>{text}</span>
    </li>
  );
}
