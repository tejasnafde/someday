# Plan: automate Play publishing in CI

Status: NOT STARTED. Start only after the first Production release of
`app.someday.capture` is approved by Google, so the workflow starts from a
known-good state. (Sent for review 2026-10-03; Play internal testing has
1.18.0 (3) live.)

## Today

- `.github/workflows/play.yml` (manual): builds the `play` AAB on EAS and
  `eas submit`s it to the internal track as a DRAFT.
- Everything else (production rollout, listing text, screenshots, data safety)
  is done by hand in Play Console, via Codex computer use.

## Target

One release workflow. A version bump merged to main (or a manual dispatch) does:

1. Build the AAB (`play` profile). versionCode auto-increments on EAS.
2. `eas submit` to the **production** track with a staged rollout
   (`releaseStatus: inProgress`, `rollout` 0.2), then a later manual dispatch
   raises it to 100%. Google reviews each update by itself; no console step.
3. Sync the store listing from the repo: `store/play/en-US/` holds
   `title.txt`, `short_description.txt`, `full_description.txt`, and
   `screenshots/phone/*.png` plus `icon.png` and `feature.png`. Upload through
   the Play Developer API (`edits.listings`, `edits.images`) in one edit, so
   that a listing change is a reviewed PR.
4. Data safety from `store/play/data-safety.csv` (`applications.dataSafety`).
5. Post the result to Discord, like the APK release webhook does.

## Stays manual (one time per app, covered by the app-store-publish skill)

Creating the app, app signing enrollment, content rating (IARC), target
audience and other declarations, the reviewer sign-in details.

## Inputs already in place

- Service account `someday-play-publisher@teejayproject` (Admin on this app
  only). Key: Secret Manager `SOMEDAY_PLAY_SA_KEY`, GitHub secret `PLAY_SA_KEY`.
- Graphics source: `~/Documents/someday-play-assets/` (backed up from `/tmp/play-assets/`) (icon,
  feature graphic, 8 screenshots at 1080x2160). Move them into `store/play/`
  as the first step, because `/tmp` does not survive a reboot.

## Risks

- A staged rollout that fails review blocks later releases until fixed.
- Keep the EAS webhook guard: only `production` `.apk` builds become GitHub
  releases; AABs never do.
