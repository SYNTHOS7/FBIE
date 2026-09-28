-- FBIE product schema. This migration contains structure only; no demo or
-- weather predictions are inserted. Operational writers use a server-side
-- Supabase service credential and publish complete batches atomically.
create extension if not exists pgcrypto;

create table if not exists public.locations (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  region text,
  state text,
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.forecast_sources (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  source_url text,
  license_url text,
  created_at timestamptz not null default now()
);

create table if not exists public.forecast_runs (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.forecast_sources(id),
  issued_at timestamptz not null,
  source_run_key text not null,
  source_file_sha256 text,
  ingested_at timestamptz not null default now(),
  unique (source_id, source_run_key)
);

create table if not exists public.model_versions (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  model_kind text not null,
  artifact_path text,
  training_data_sha256 text,
  trained_through timestamptz,
  evaluation jsonb not null default '{}'::jsonb,
  approved_for_publication boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.prediction_batches (
  id uuid primary key default gen_random_uuid(),
  forecast_run_id uuid not null references public.forecast_runs(id),
  model_version_id uuid not null references public.model_versions(id),
  status text not null default 'staging' check (status in ('staging', 'published', 'failed')),
  expected_count integer check (expected_count >= 0),
  published_at timestamptz,
  created_at timestamptz not null default now(),
  unique (forecast_run_id, model_version_id),
  check ((status = 'published') = (published_at is not null))
);

create table if not exists public.risk_predictions (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references public.prediction_batches(id) on delete cascade,
  location_id uuid not null references public.locations(id),
  variable text not null check (variable in ('rainfall_mm', 'temperature_c', 'wind_speed_mps')),
  valid_at timestamptz not null,
  lead_day smallint not null check (lead_day between 1 and 10),
  forecast_value double precision,
  risk_probability double precision not null check (risk_probability between 0 and 1),
  error_threshold double precision not null check (error_threshold >= 0),
  predicted_error_p10 double precision,
  predicted_error_p90 double precision,
  failure_modes jsonb not null default '{}'::jsonb,
  explanation jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (batch_id, location_id, variable, valid_at),
  check (predicted_error_p10 is null or predicted_error_p90 is null or predicted_error_p10 <= predicted_error_p90)
);

create table if not exists public.saved_locations (
  user_id uuid not null references auth.users(id) on delete cascade,
  location_id uuid not null references public.locations(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, location_id)
);

create index if not exists risk_predictions_location_variable_valid_idx
  on public.risk_predictions(location_id, variable, valid_at);
create index if not exists prediction_batches_published_idx
  on public.prediction_batches(published_at desc) where status = 'published';
create index if not exists saved_locations_user_idx
  on public.saved_locations(user_id);

alter table public.locations enable row level security;
alter table public.forecast_sources enable row level security;
alter table public.forecast_runs enable row level security;
alter table public.model_versions enable row level security;
alter table public.prediction_batches enable row level security;
alter table public.risk_predictions enable row level security;
alter table public.saved_locations enable row level security;

create policy "read active locations" on public.locations for select to anon, authenticated using (active);
create policy "read forecast sources" on public.forecast_sources for select to anon, authenticated using (true);
create policy "read published forecast runs" on public.forecast_runs for select to anon, authenticated
  using (exists (select 1 from public.prediction_batches b where b.forecast_run_id = forecast_runs.id and b.status = 'published'));
create policy "read approved models" on public.model_versions for select to anon, authenticated
  using (approved_for_publication);
create policy "read published batches" on public.prediction_batches for select to anon, authenticated
  using (status = 'published' and exists (
    select 1 from public.model_versions m where m.id = model_version_id and m.approved_for_publication
  ));
create policy "read published predictions" on public.risk_predictions for select to anon, authenticated
  using (exists (select 1 from public.prediction_batches b where b.id = batch_id and b.status = 'published'));
create policy "select own saved locations" on public.saved_locations for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "insert own saved locations" on public.saved_locations for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "delete own saved locations" on public.saved_locations for delete to authenticated
  using ((select auth.uid()) = user_id);
