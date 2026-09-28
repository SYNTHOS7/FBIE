-- Stable public read contract for the FastAPI service. Security invoker keeps
-- the underlying RLS policies in force for anon/authenticated clients.
create or replace view public.api_published_risk
with (security_invoker = true)
as
select
  l.slug as region_id,
  case p.variable
    when 'rainfall_mm' then 'rainfall'
    when 'temperature_c' then 'temperature'
    when 'wind_speed_mps' then 'wind'
  end as variable,
  p.lead_day,
  p.risk_probability as probability,
  case
    when p.risk_probability >= 0.7 then 'high'
    when p.risk_probability >= 0.4 then 'elevated'
    else 'low'
  end as risk_level,
  coalesce(p.explanation->>'headline', 'Forecast reliability estimate') as headline,
  coalesce(p.explanation->>'summary', '') as explanation,
  coalesce(p.explanation->'drivers', '[]'::jsonb) as drivers,
  p.failure_modes,
  r.issued_at as forecast_time,
  p.valid_at as valid_time,
  m.code as model_version,
  jsonb_build_object('code', s.code, 'name', s.name, 'url', s.source_url) as source,
  jsonb_build_object(
    'prediction_id', p.id,
    'batch_id', b.id,
    'model_version_id', m.id,
    'source_run_key', r.source_run_key,
    'published_at', b.published_at,
    'error_threshold', p.error_threshold,
    'forecast_value', p.forecast_value,
    'predicted_error_p10', p.predicted_error_p10,
    'predicted_error_p90', p.predicted_error_p90
  ) as provenance
from public.risk_predictions p
join public.prediction_batches b on b.id = p.batch_id
join public.forecast_runs r on r.id = b.forecast_run_id
join public.forecast_sources s on s.id = r.source_id
join public.model_versions m on m.id = b.model_version_id
join public.locations l on l.id = p.location_id
where b.status = 'published'
  and m.approved_for_publication
  and l.active;

grant select on public.api_published_risk to anon, authenticated;
