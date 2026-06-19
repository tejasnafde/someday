-- Re-hosted link-preview images. og:image URLs from source sites are often
-- signed CDN URLs that expire (Instagram/FB scontent, S3 presigned, etc.),
-- producing broken JPEGs over time. We download them at unfurl time and
-- re-host here so previews are permanent. Public bucket, uploads via service key.
INSERT INTO storage.buckets (id, name, public)
VALUES ('previews', 'previews', true)
ON CONFLICT DO NOTHING;
