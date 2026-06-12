import * as Application from "expo-application";
import * as FileSystem from "expo-file-system/legacy";
import * as IntentLauncher from "expo-intent-launcher";

const RELEASES_API = "https://api.github.com/repos/tejasnafde/someday/releases/latest";

export interface ApkUpdate {
  version: string;
  apkUrl: string;
}

function newer(latest: string, current: string): boolean {
  const a = latest.split(".").map(Number);
  const b = current.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if ((a[i] ?? 0) > (b[i] ?? 0)) return true;
    if ((a[i] ?? 0) < (b[i] ?? 0)) return false;
  }
  return false;
}

export async function checkForApkUpdate(): Promise<ApkUpdate | null> {
  try {
    const res = await fetch(RELEASES_API, { headers: { Accept: "application/vnd.github+json" } });
    if (!res.ok) return null;
    const release = await res.json();
    const version = (release.tag_name ?? "").replace(/^v/, "");
    const apk = (release.assets ?? []).find((a: { name: string }) => a.name.endsWith(".apk"));
    const current = Application.nativeApplicationVersion ?? "0.0.0";
    if (apk && version && newer(version, current)) {
      return { version, apkUrl: apk.browser_download_url };
    }
    return null;
  } catch {
    return null;
  }
}

export async function downloadAndInstall(update: ApkUpdate) {
  const dest = `${FileSystem.cacheDirectory}someday-${update.version}.apk`;
  const result = await FileSystem.downloadAsync(update.apkUrl, dest);
  if (result.status !== 200) throw new Error(`download failed (${result.status})`);

  // The package installer can't read file:// URIs on Android 7+ —
  // FileProvider content:// URI is required.
  const contentUri = await FileSystem.getContentUriAsync(result.uri);
  await IntentLauncher.startActivityAsync("android.intent.action.INSTALL_PACKAGE", {
    data: contentUri,
    flags: 1, // FLAG_GRANT_READ_URI_PERMISSION
  });
}
