# Supabase database

Apply these migrations in order:

1. `migrations/202609280001_core.sql` — core tables and row-level policies.
2. `migrations/202609280002_api_view.sql` — public approved-prediction read view.
3. `migrations/202609280003_publication.sql` — atomic batch publication function.

No weather predictions are seeded. Public clients can read only active locations and approved, published results. The service role writes source metadata, model versions, and results. Keep it off the frontend. Users can read and change only their own saved locations.

A prediction batch may be published only when its model is approved, its row count matches, and every valid time falls within the supported forecast horizon. The API reads the latest available result through `public.api_published_risk`.