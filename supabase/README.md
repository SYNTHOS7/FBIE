# Supabase database

Apply these migrations in order:

1. `migrations/202609280001_core.sql` — core tables and row-level policies.
2. `migrations/202609280002_api_view.sql` — public approved-prediction read view.
3. `migrations/202609280003_publication.sql` — atomic batch publication function.
4. `migrations/202609280004_verification.sql` — labelled comparison records and six research locations.
5. `migrations/202609280005_model_artifact.sql` — small versioned research-model artifact.
6. `migrations/20260930141824_tighten_publication_reads.sql` — private Data API grants and approved-model policies.

No weather predictions are seeded. The browser uses Supabase Auth for sign-in, then the FastAPI service for saved locations and published data. FBIE application tables and the view have no direct `anon` or `authenticated` grants through Supabase's Data API. Keep the Postgres connection string and writer credentials off the frontend. Saved-location operations are scoped to a token validated by Supabase Auth.

A prediction batch may be published only when its model is approved, its row count matches, and every valid time falls within the supported forecast horizon. The API reads the latest available result through `public.api_published_risk`.
