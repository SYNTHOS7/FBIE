-- Publication is atomic; callable only by the server-side service role.
create or replace function public.publish_prediction_batch(p_batch_id uuid)
returns void language plpgsql security definer set search_path = public as $$
declare
  selected_batch public.prediction_batches%rowtype;
  actual_count integer;
  approved boolean;
begin
  select * into selected_batch from public.prediction_batches
    where id = p_batch_id for update;
  if not found or selected_batch.status <> 'staging' then
    raise exception 'batch missing or not staging';
  end if;
  select approved_for_publication into approved from public.model_versions
    where id = selected_batch.model_version_id;
  if not coalesce(approved, false) then
    raise exception 'model is not approved';
  end if;
  select count(*) into actual_count from public.risk_predictions
    where batch_id = p_batch_id;
  if selected_batch.expected_count is null or actual_count = 0
     or actual_count <> selected_batch.expected_count then
    raise exception 'batch incomplete: expected %, found %',
      selected_batch.expected_count, actual_count;
  end if;
  if exists (
    select 1 from public.risk_predictions p
    join public.forecast_runs r on r.id = selected_batch.forecast_run_id
    where p.batch_id = p_batch_id
      and (p.valid_at <= r.issued_at or p.valid_at > r.issued_at + interval '10 days')
  ) then
    raise exception 'prediction valid times outside supported lead';
  end if;
  update public.prediction_batches set status = 'published', published_at = now()
    where id = p_batch_id;
end;
$$;

revoke all on function public.publish_prediction_batch(uuid) from public, anon, authenticated;
grant execute on function public.publish_prediction_batch(uuid) to service_role;
