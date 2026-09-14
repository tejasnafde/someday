"use client";

import { useEffect, useState } from "react";
import { detectInstallPlatform, type InstallPlatform } from "@/lib/installPlatform.cjs";

/**
 * Latest Android build. This URL always serves the newest release, so it never
 * needs updating when a version ships. Keep it here, not inline in a component:
 * two places link to it and a stale copy would hand users an old APK.
 */
export const APK_URL = "https://github.com/tejasnafde/someday/releases/latest/download/someday.apk";

/**
 * The visitor's platform, or null until the browser has been read. Detection
 * needs `window` and `navigator`, so it cannot run during the server render -
 * callers must treat null as "not known yet" and render nothing.
 */
export function useInstallPlatform(): InstallPlatform | null {
  const [platform, setPlatform] = useState<InstallPlatform | null>(null);

  useEffect(() => {
    const standalone = window.matchMedia("(display-mode: standalone)").matches
      || Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
    setPlatform(detectInstallPlatform({
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      maxTouchPoints: navigator.maxTouchPoints,
      standalone,
    }));
  }, []);

  return platform;
}
