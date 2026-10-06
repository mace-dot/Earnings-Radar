-- Run in Supabase SQL Editor once. These tables contain public research only.
-- Existing SQLite files are preserved. No personal notes/accounts are published.
begin;
create table if not exists public.radar_events (
  id text primary key check (length(id) = 64),
  provider text not null,
  provider_event_id text not null,
  content_hash text not null,
  title text not null,
  url text not null check (url like 'https://%'),
  institution text not null default '',
  published_at timestamptz not null,
  retrieved_at timestamptz not null,
  first_seen_at timestamptz not null default now(),
  tickers jsonb not null default '[]' check (jsonb_typeof(tickers) = 'array'),
  analysis jsonb not null check (jsonb_typeof(analysis) = 'object'),
  unique (provider, provider_event_id, content_hash)
);
create index if not exists radar_events_published on public.radar_events (published_at desc);
create table if not exists public.radar_status (
  id text primary key check (id = 'collector'),
  updated_at timestamptz not null,
  payload jsonb not null check (jsonb_typeof(payload) = 'object')
);
alter table public.radar_events enable row level security;
alter table public.radar_status enable row level security;
revoke all on public.radar_events, public.radar_status from anon, authenticated;
grant select, insert, update on public.radar_events, public.radar_status to service_role;
-- No public policies: only the server and scheduled collector can access tables.
commit;
