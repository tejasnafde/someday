export type InstallPlatform = "installed" | "android" | "ios" | "desktop";

export function detectInstallPlatform(input: {
  userAgent: string;
  platform: string;
  maxTouchPoints: number;
  standalone: boolean;
}): InstallPlatform;
