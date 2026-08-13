# Install and Share Adoption Design

## Goal

Make Someday easy to install from Settings and reliably available as a share
destination across Android browsers, Instagram, and other apps. Preserve the
existing link-first capture flow while handling richer Android share payloads
without silently disappearing or failing.

## Install experience

Settings includes an **Install Someday** section whose content follows the
current platform and installation context:

- Android recommends the native APK because it provides the best share-sheet
  integration. Its download action uses GitHub's stable
  `releases/latest/download/someday.apk` URL, so the same link always resolves
  to the latest published APK.
- iPhone and iPad show short Safari instructions for Share → Add to Home Screen.
- Desktop browsers show install guidance only where the browser exposes an
  install prompt; otherwise Settings explains how to use the browser menu.
- Standalone browser installations identify themselves as already installed.

The existing native self-updater remains the update mechanism for installed
APKs. It checks the latest GitHub release, downloads a newer signed APK, and
hands it to Android's package installer.

## Android native sharing

The native configuration explicitly accepts one-item `ACTION_SEND` payloads
with `text/*`, `image/*`, and `video/*` MIME types. This prevents Instagram or
an OEM Android build from filtering Someday out when a reel share contains
media in addition to, or instead of, plain text.

The React Native entry point passes shared files into the capture flow as well
as the existing shared text and extracted URL:

- If the payload contains a URL, the existing unfurl, title, circle selection,
  and save behavior remains unchanged.
- If a media payload contains text but no recognized URL, the text remains
  editable and can be saved as a text-only idea.
- If a media-only payload contains neither a URL nor useful text, the capture
  flow explains that the source app did not provide a link and gives the user
  a paste field. Someday does not upload or retain the shared media in this
  iteration.

Accepting `*/*` is deliberately excluded because it would advertise Someday
for documents, contacts, audio, and other content the product cannot capture.

## Installed web-app sharing

The web manifest declares a POST Web Share Target for text, title, and URL. A
same-origin receiving route normalizes those fields, extracts an HTTP(S) URL,
and routes an authenticated user into the existing add-to-circle flow. It
preserves the received values through authentication when necessary.

The APK remains the recommended Android installation because native share
targets are more broadly supported than Web Share Target and can accept rich
Instagram payloads.

## Failure handling

- APK release lookup, download, or installer failures remain recoverable and
  display an actionable retry message.
- Unsupported rich shares open the app and request a paste instead of leaving
  Someday absent from the share sheet.
- Web share payloads with no useful text or URL land on an editable add screen
  rather than creating empty records.
- Platform detection is progressive enhancement: Settings always retains a
  usable manual instruction if an install API is unavailable.

## Verification

Automated tests cover:

- Android config generation includes `SEND` plus `text/*`, `image/*`, and
  `video/*` while excluding `*/*`.
- Shared-payload normalization extracts URLs and produces the correct fallback
  for media-only payloads.
- The web manifest exposes the expected POST share target.
- The web receiver normalizes title, text, and URL parameters safely.
- Settings renders the appropriate Android, iOS, standalone, and desktop state.

Release acceptance covers type checking, production web build, generated
Android manifest inspection, browser smoke tests, cold and warm share launches,
logged-out capture, latest-APK resolution, upgrade installation, and a final
Instagram test on the affected OnePlus device.
