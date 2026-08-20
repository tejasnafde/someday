# Idempotent APK Release Upload

## Problem

The EAS webhook creates a GitHub release and uploads `someday.apk` in a background task. If another recovery path uploads the asset first, GitHub returns `422 Unprocessable Entity` with an `already_exists` error. The webhook currently treats that expected race as a production 500 and never reaches release notifications.

## Design

Keep `someday.apk` as the stable asset name expected by the native updater. Before uploading, inspect the release assets. If an uploaded `someday.apk` already exists with the same byte size as the downloaded EAS artifact, treat publication as successful and continue notifications.

The preflight check is only an optimization. A competing uploader can still win after the check, so a 422 response must trigger the same asset lookup and size verification. Only a matching, fully uploaded asset is idempotent success. A missing asset, a size mismatch, a non-uploaded state, or any unrelated GitHub error remains a failure.

GitHub upload failures should include a bounded, secret-scrubbed response summary in server diagnostics. The upload URL itself contains no credential, but the GitHub bearer token must never be logged.

## Tests

- An already uploaded asset with the same size skips the upload and completes notifications.
- A race that returns 422 succeeds only after GitHub reports a matching uploaded asset.
- A same-name asset with a different size fails.
- An unrelated 422 remains an error and includes a bounded safe diagnostic.
- Existing webhook and API tests remain green.

## Deployment

Merge through the normal API workflow, confirm the Cloud Run revision receives all traffic, and verify the latest GitHub release remains downloadable. No database or configuration migration is required.
