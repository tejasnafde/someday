function detectInstallPlatform({ userAgent, platform, maxTouchPoints, standalone }) {
  if (standalone || /SomedayNative\//i.test(userAgent)) return "installed";
  if (/Android/i.test(userAgent)) return "android";
  if (/iPad|iPhone|iPod/i.test(userAgent)) return "ios";
  if (platform === "MacIntel" && maxTouchPoints > 1) return "ios";
  return "desktop";
}

module.exports = { detectInstallPlatform };
