-- The small baseline JSON can live in Postgres for an ephemeral scheduled worker.
-- Future large binary model artifacts should be kept in versioned object storage.
alter table public.model_versions
  add column if not exists artifact_json jsonb;
