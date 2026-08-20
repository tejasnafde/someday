# Idempotent APK Release Upload

## Problem

The EAS webhook creates a GitHub release and uploads `someday.apk` in a background task. If another recovery path uploads the asset first, GitHub returns `422 Unprocessable Entity` with an `already_exists` error. The webhook currently treats that expected race as a production 500 and never reaches release notifications.

## Design

Keep `someday.apk` as the stable asset name expected by the native updater. Before uploading, inspect the release assets. If an uploaded `someday.apk` already exists with the same byte size as the downloaded EAS artifact, treat publication as successful without sending another push or Discord notification. Only the process that receives a successful upload response sends release notifications, preventing concurrent workers from fanning out duplicates.

The preflight check is only an optimization and a transient or malformed lookup response does not block the upload. A competing uploader can still win after the check, so a 422 response must trigger the same asset lookup and size verification. Only a matching, fully uploaded asset is idempotent success. A missing asset, a size mismatch, a non-uploaded state, or any unrelated GitHub error remains a failure. If race verification itself fails, preserve the original upload diagnostic. APK bytes stream from the temporary file with an explicit `Content-Length`, as required by GitHub's asset endpoint.

GitHub upload failures should include a bounded, secret-scrubbed response summary in server diagnostics. The upload URL itself contains no credential, but the GitHub bearer token must never be logged.

## Tests

- An already uploaded asset with the same size skips the upload and duplicate notifications.
- A race that returns 422 succeeds only after GitHub reports a matching uploaded asset, without duplicate notifications.
- A normal 201 upload sends release notifications once.
- A transient preflight failure does not block a normal upload.
- A malformed preflight response does not block a normal upload.
- A same-name asset with a different size fails.
- An unrelated 422 remains an error and includes a bounded safe diagnostic.
- Unexpected JSON error shapes, control characters, and empty artifacts remain safe diagnostic failures.
- The upload request has the exact APK `Content-Length` and consumes every streamed byte.
- One broken release does not prevent recovery from attempting later releases.
- Existing webhook and API tests remain green.

## Deployment

Merge through the normal API workflow, confirm the Cloud Run revision receives all traffic, and verify the latest GitHub release remains downloadable. No database or configuration migration is required.
