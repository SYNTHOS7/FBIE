-- Independent reference provenance is retained alongside verification outcomes.
-- ERA5/reanalysis comparisons must never be presented as station observations.
create table if not exists public.verification_records (
  id uuid primary key default gen_random_uuid(),
  prediction_id uuid not null unique references public.risk_predictions(id) on delete cascade,
  observed_at timestamptz not null,
  observed_value double precision not null,
  absolute_error double precision not null check (absolute_error >= 0),
  busted boolean not null,
  reference_source text not null,
  reference_kind text not null check (reference_kind in ('station_observation', 'satellite_estimate', 'reanalysis_proxy')),
  reference_file_sha256 text,
  verified_at timestamptz not null default now(),
  check (observed_value = observed_value and absolute_error = absolute_error)
);

create index if not exists verification_records_verified_at_idx
  on public.verification_records (verified_at desc);
alter table public.verification_records enable row level security;
create policy "read published verification" on public.verification_records
  for select to anon, authenticated using (
    exists (select 1 from public.risk_predictions p
      join public.prediction_batches b on b.id = p.batch_id
      where p.id = prediction_id and b.status = 'published')
  );

-- Seed selected research locations; this inserts no forecast or prediction.
insert into public.locations (slug, name, state, region, latitude, longitude) values
  ('ahmedabad', 'Ahmedabad', 'Gujarat', 'Western India', 23.0225, 72.5714),
  ('bengaluru', 'Bengaluru', 'Karnataka', 'Southern India', 12.9716, 77.5946),
  ('delhi', 'Delhi', 'Delhi', 'Northern India', 28.6139, 77.2090),
  ('jaipur', 'Jaipur', 'Rajasthan', 'Northern India', 26.9124, 75.7873),
  ('kolkata', 'Kolkata', 'West Bengal', 'Eastern India', 22.5726, 88.3639),
  ('mumbai', 'Mumbai', 'Maharashtra', 'Western India', 19.0760, 72.8777)
on conflict (slug) do nothing;

insert into public.forecast_sources (code, name, source_url, license_url) values
  ('open_meteo_ecmwf_ifs_hres_9km', 'Open-Meteo ECMWF IFS HRES 9 km Single Runs',
   'https://open-meteo.com/en/docs/single-runs-api', 'https://open-meteo.com/en/terms')
on conflict (code) do nothing;
