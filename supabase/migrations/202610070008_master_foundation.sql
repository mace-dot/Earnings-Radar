-- Additive foundation. Existing radar_* tables remain intact.
begin;
create table if not exists public.securities (
 symbol text primary key, cik text, name text not null, exchange text,
 active boolean not null default true, asset_type text not null default 'unverified',
 sector text not null default 'Unclassified', industry text, sector_etf text,
 source text not null, as_of timestamptz not null
);
create index if not exists securities_name_idx on public.securities(lower(name));
create table if not exists public.earnings_events (
 id text primary key, symbol text not null references public.securities(symbol),
 report_date date not null, timing text not null default 'unknown',
 date_status text not null check(date_status in ('estimated','conflicting','confirmed')),
 sources jsonb not null, as_of timestamptz not null, payload jsonb not null default '{}'
);
create table if not exists public.daily_bars (
 id text primary key, symbol text not null references public.securities(symbol),
 session_date date not null, close numeric not null check(close>0), open numeric,
 high numeric, low numeric, volume bigint, source text not null, feed text not null,
 as_of timestamptz not null, available_at timestamptz not null,
 unique(symbol, session_date, source, feed)
);
create table if not exists public.option_snapshots (
 id text primary key, symbol text not null references public.securities(symbol),
 contract_id text not null, expiry date not null, strike numeric not null,
 source text not null, feed text not null, as_of timestamptz not null,
 payload jsonb not null
);
create table if not exists public.estimate_revisions (
 id text primary key, symbol text not null references public.securities(symbol),
 period text not null, source text not null, as_of timestamptz not null,
 payload jsonb not null
);
create table if not exists public.news_items (
 id text primary key, symbol text references public.securities(symbol),
 headline text not null, url text not null, source text not null,
 published_at timestamptz not null, retrieved_at timestamptz not null, payload jsonb not null default '{}'
);
create table if not exists public.features (
 id text primary key, symbol text not null references public.securities(symbol),
 event_id text references public.earnings_events(id), version text not null,
 as_of timestamptz not null, observations jsonb not null, values jsonb not null,
 missing_reasons jsonb not null
);
create table if not exists public.lines (
 id text primary key, symbol text not null references public.securities(symbol),
 event_id text references public.earnings_events(id), kind text not null,
 as_of timestamptz not null, expires_at timestamptz not null,
 source text not null, payload jsonb not null
);
create table if not exists public.line_sides (
 id text primary key, line_id text not null references public.lines(id),
 side text not null check(side in ('BULL','BEAR')), as_of timestamptz not null,
 payload jsonb not null
);
create table if not exists public.picks (
 id text primary key, line_id text not null references public.lines(id),
 symbol text not null, side text not null check(side in ('BULL','BEAR')),
 as_of timestamptz not null, expires_at timestamptz not null,
 strategy_version text not null, observations jsonb not null,
 payload jsonb not null
);
create table if not exists public.pick_outcomes (
 id text primary key, pick_id text not null unique references public.picks(id),
 graded_at timestamptz not null, source text not null, payload jsonb not null
);
create table if not exists public.model_registry (
 id text primary key, line_kind text not null, trained_at timestamptz not null,
 status text not null check(status in ('challenger','validated','rejected')),
 payload jsonb not null
);
create table if not exists public.model_portfolio_trades (
 id text primary key, pick_id text references public.picks(id),
 as_of timestamptz not null, payload jsonb not null
);
create table if not exists public.engine_runs (
 id text primary key, job text not null, as_of timestamptz not null,
 status text not null, payload jsonb not null
);
create table if not exists public.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 payload jsonb not null default '{}', updated_at timestamptz not null default now()
);
create table if not exists public.lineups (
 id uuid primary key default gen_random_uuid(), owner_id uuid not null references auth.users(id) on delete cascade,
 payload jsonb not null default '{}', created_at timestamptz not null default now()
);
create table if not exists public.lineup_items (
 id uuid primary key default gen_random_uuid(), owner_id uuid not null references auth.users(id) on delete cascade,
 lineup_id uuid not null references public.lineups(id) on delete cascade,
 line_side_id text not null references public.line_sides(id), payload jsonb not null default '{}'
);
create table if not exists public.alerts (
 id uuid primary key default gen_random_uuid(), owner_id uuid not null references auth.users(id) on delete cascade,
 opted_in boolean not null default false, payload jsonb not null default '{}'
);
-- Public market data stays server-read until vendor redistribution rights are verified.
-- No service credential or unrestricted market table access in the browser.
do $$
declare t text;
begin
 foreach t in array array['securities','earnings_events','daily_bars','option_snapshots','estimate_revisions',
 'news_items','features','lines','line_sides','picks','pick_outcomes','model_registry','model_portfolio_trades','engine_runs'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('grant all on public.%I to service_role',t);
 end loop;
 foreach t in array array['profiles','lineups','lineup_items','alerts'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('grant select,insert,update,delete on public.%I to authenticated',t);
  if t = 'profiles' then
   execute format('create policy owner_access on public.%I for all to authenticated using (id=auth.uid()) with check (id=auth.uid())',t);
  else
   execute format('create policy owner_access on public.%I for all to authenticated using (owner_id=auth.uid()) with check (owner_id=auth.uid())',t);
  end if;
 end loop;
end $$;
create or replace function public.radar_immutable_pick() returns trigger language plpgsql as $$
begin raise exception 'Published picks are immutable'; end $$;
create trigger immutable_pick before update or delete on public.picks for each row execute function public.radar_immutable_pick();
create or replace function public.radar_lineup_owner() returns trigger language plpgsql security invoker set search_path=public as $$
begin
 if not exists(select 1 from public.lineups where id=new.lineup_id and owner_id=new.owner_id) then
  raise exception 'Lineup owner mismatch';
 end if;
 return new;
end $$;
create trigger lineup_owner before insert or update on public.lineup_items for each row execute function public.radar_lineup_owner();
commit;
