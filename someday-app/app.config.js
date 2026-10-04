// Build-time variants on top of app.json. The "play" EAS profile sets
// APP_VARIANT=play. Google Play forbids self-updating outside Play, so the Play
// build drops the in-app APK updater: no REQUEST_INSTALL_PACKAGES, and the
// update banner stays hidden (extra.distribution). SYSTEM_ALERT_WINDOW comes in
// through a library, is unused, and draws reviewer questions, so it goes too.
// The sideloaded APK (production profile) is unchanged.
const PLAY_BLOCKED = [
  "android.permission.REQUEST_INSTALL_PACKAGES",
  "android.permission.SYSTEM_ALERT_WINDOW",
];

// "appstore" (iOS App Store) gets the same distribution flag: no APK updater.
module.exports = ({ config }) => {
  const variant = process.env.APP_VARIANT;
  if (variant !== "play" && variant !== "appstore") return config;
  return {
    ...config,
    android: {
      ...config.android,
      permissions: (config.android.permissions ?? []).filter((p) => !PLAY_BLOCKED.includes(p)),
      blockedPermissions: [...(config.android.blockedPermissions ?? []), ...PLAY_BLOCKED],
    },
    extra: { ...config.extra, distribution: variant },
  };
};
