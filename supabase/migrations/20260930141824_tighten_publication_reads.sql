-- The public product reads through FastAPI using a server-side Postgres role.
-- Supabase Auth remains public, but the Data API must not expose FBIE tables.
-- Keep RLS as defense in depth in case grants are changed later.
revoke all on table
  public.locations,
  public.forecast_sources,
  public.forecast_runs,
  public.model_versions,
  public.prediction_batches,
  public.risk_predictions,
  public.verification_records,
  public.saved_locations,
  public.api_published_risk
from anon, authenticated;

drop policy if exists "read published forecast runs" on public.forecast_runs;
create policy "read approved published forecast runs" on public.forecast_runs
  for select to anon, authenticated using (
    exists (
      select 1 from public.prediction_batches b
      join public.model_versions m on m.id = b.model_version_id
      where b.forecast_run_id = forecast_runs.id
        and b.status = 'published' and m.approved_for_publication
    )
  );

drop policy if exists "read published predictions" on public.risk_predictions;
create policy "read approved published predictions" on public.risk_predictions
  for select to anon, authenticated using (
    exists (
      select 1 from public.prediction_batches b
      join public.model_versions m on m.id = b.model_version_id
      where b.id = risk_predictions.batch_id
        and b.status = 'published' and m.approved_for_publication
    )
  );

drop policy if exists "read published verification" on public.verification_records;
create policy "read approved published verification" on public.verification_records
  for select to anon, authenticated using (
    exists (
      select 1 from public.risk_predictions p
      join public.prediction_batches b on b.id = p.batch_id
      join public.model_versions m on m.id = b.model_version_id
      where p.id = verification_records.prediction_id
        and b.status = 'published' and m.approved_for_publication
    )
  );
