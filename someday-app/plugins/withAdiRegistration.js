// Copies adi-registration.properties into the Android assets. Google's Android
// developer verification reads this file from a signed APK to prove that the
// GlycoCare developer account owns app.someday.capture and its signing key.
// The token is not a secret: it proves nothing without the signing key.
const fs = require("fs");
const path = require("path");
const { withDangerousMod } = require("expo/config-plugins");

module.exports = function withAdiRegistration(config) {
  return withDangerousMod(config, [
    "android",
    async (c) => {
      const dir = path.join(c.modRequest.platformProjectRoot, "app/src/main/assets");
      fs.mkdirSync(dir, { recursive: true });
      fs.copyFileSync(
        path.join(c.modRequest.projectRoot, "adi-registration.properties"),
        path.join(dir, "adi-registration.properties"),
      );
      return c;
    },
  ]);
};
