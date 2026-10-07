begin;
alter table public.radar_events add column if not exists evidence_meta jsonb not null default '{}';
alter table public.radar_events add column if not exists story_key text;
alter table public.radar_events add column if not exists provenance text not null default 'primary';
alter table public.radar_events add column if not exists claim_type text not null default 'primary_evidence';
alter table public.radar_events add column if not exists backfill boolean not null default true;
create table if not exists public.radar_watchlists (
 user_id uuid not null references auth.users(id) on delete cascade,
 symbol text not null check(symbol ~ '^[A-Z][A-Z0-9.-]{0,9}$'),
 created_at timestamptz not null default now(), primary key(user_id,symbol)
);
alter table public.radar_watchlists enable row level security;
drop policy if exists own_watchlist on public.radar_watchlists;
create policy own_watchlist on public.radar_watchlists for all to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
revoke all on public.radar_watchlists from anon;
grant select,insert,delete on public.radar_watchlists to authenticated;
grant select,insert,delete on public.radar_watchlists to service_role;
create or replace function public.radar_watchlist_limit() returns trigger language plpgsql set search_path=public as $$
begin
 perform pg_advisory_xact_lock(hashtextextended(new.user_id::text,0));
 if not exists(select 1 from public.radar_watchlists where user_id=new.user_id and symbol=new.symbol)
 and (select count(*) from public.radar_watchlists where user_id=new.user_id)>=20 then
 raise exception 'Watchlist limit is 20 stocks'; end if;
 return new;
end; $$;
drop trigger if exists radar_watchlist_limit on public.radar_watchlists;
create trigger radar_watchlist_limit before insert on public.radar_watchlists for each row execute function public.radar_watchlist_limit();
create table if not exists public.radar_collection_state (
 id boolean primary key default true check(id), owner uuid, lease_until timestamptz,
 last_started timestamptz, last_finished timestamptz, last_error text
);
alter table public.radar_collection_state enable row level security;
revoke all on public.radar_collection_state from anon,authenticated;
grant select,insert,update on public.radar_collection_state to service_role;
insert into public.radar_collection_state(id) values(true) on conflict do nothing;
create or replace function public.radar_claim_collection(p_owner uuid) returns boolean
language plpgsql security definer set search_path=public as $$
begin
 update public.radar_collection_state set owner=p_owner,lease_until=now()+interval '5 minutes',last_started=now(),last_error=null
 where id=true and (lease_until is null or lease_until<now()) and (last_finished is null or last_finished<now()-interval '15 minutes');
 return found;
end; $$;
revoke all on function public.radar_claim_collection(uuid) from public,anon,authenticated;
grant execute on function public.radar_claim_collection(uuid) to service_role;
-- Existing records and personal legacy SQLite tables are untouched.
commit;
