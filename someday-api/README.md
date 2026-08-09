# someday-api

FastAPI service on Cloud Run, `teejayproject` / `asia-south1`.
Conventions and architecture live in `../CLAUDE.md` and `../docs/`. This file is
the operational knowledge that is expensive to rediscover.

## Deploying

**GitHub Actions is the only deploy path.** `.github/workflows/api.yml` runs on
push to `main` touching `someday-api/**`.

`cloudbuild-production.yaml` still exists and still works, but its Cloud Build
trigger `deploy-someday-api` is **disabled on purpose**. Both used to fire on the
same push and race each other. The loser failed with `ABORTED: Conflict`, which
also posted a false failure alert to Discord.

Keep the two files in sync anyway. The trigger is one flag away from returning,
and a drifted `cloudbuild-production.yaml` would then deploy the wrong config.

### Re-enabling or disabling the trigger

There is **no `gcloud builds triggers disable`**, and the obvious REST call is
rejected:

```
PATCH .../triggers/<id>?updateMask=disabled   ->  400 invalid argument
```

Fetch the whole trigger, flip the field, PATCH the full body back:

```sh
GC=/opt/homebrew/share/google-cloud-sdk/bin/gcloud
TOKEN=$($GC --configuration=personal auth print-access-token)
ID=b0d39758-5ec5-43ff-b682-120487b99c62
U="https://cloudbuild.googleapis.com/v1/projects/teejayproject/triggers/${ID}"

curl -s -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: teejayproject" "$U" > /tmp/t.json
python3 -c "import json;d=json.load(open('/tmp/t.json'));d['disabled']=False;json.dump(d,open('/tmp/t.json','w'))"
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: teejayproject" \
  -H "Content-Type: application/json" --data @/tmp/t.json "$U"
rm -f /tmp/t.json
```

## Secrets: one blob, not one per value

Every credential is in a single Secret Manager entry, `someday-api-config`, a
JSON object. Secret Manager bills **per secret version per month, not per byte**,
with only six free, so nine secrets cost nine times what one object holding the
same nine values costs.

Cloud Run maps one secret to one env var, so the fan-out happens in process:
`load_config_blob()` in `config/settings.py` expands `SOMEDAY_CONFIG` into
`os.environ`. It runs at **import time**, before `Settings()` at the bottom of
that module. A FastAPI startup hook is too late, because pydantic validates at
import rather than at first request.

Existing environment variables win over the blob, so a locally exported value
still overrides it.

### Adding or changing a credential

Edit the JSON. Do not add a flag to the deploy files.

```sh
gcloud --configuration=personal secrets versions access latest \
  --secret=someday-api-config > /tmp/c.json
# edit /tmp/c.json
gcloud --configuration=personal secrets versions add someday-api-config \
  --data-file=/tmp/c.json && rm /tmp/c.json
```

**A new version does not reach a running service on its own.** Cloud Run resolves
`:latest` when an *instance starts*, not per request, so instances already
serving keep the old value and you get a mixed fleet. Force a revision:

```sh
gcloud --configuration=personal run services update someday-api \
  --region=asia-south1 --project=teejayproject --update-labels=rollout=$(date +%s)
```

### The K_SERVICE guard

`load_config_blob()` raises if `SOMEDAY_CONFIG` is missing **and** `K_SERVICE` is
set. `K_SERVICE` is set only by Cloud Run.

The guard is deliberately not on `APP_ENV=production`, because that is also how a
local script points itself at the production database
(`scripts/backfill_preview_images.py` documents exactly that), and those runs
read `.env.production` and must keep working.

Without the guard the safety net would be accidental: a deploy that forgot
`--set-secrets` only fails because `.dockerignore` keeps `.env.production` out of
the image, so pydantic finds nothing and raises. Ship that file and the same
mistake silently starts the service on stale committed values.

## Rolling back

Roll back the Cloud Run **revision**, or revert the whole change. Reverting only
the deploy YAML does not work: the deployed image still expands the blob and
refuses to start on Cloud Run without `SOMEDAY_CONFIG`, so the deploy fails and
the old revision keeps serving. That failure mode is the intended one.
