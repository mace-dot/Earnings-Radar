begin;
create table if not exists public.radar_data_cache (
 id text primary key, payload jsonb not null default '{}', last_attempt timestamptz,
 lease_until timestamptz,last_error text
);
alter table public.radar_data_cache enable row level security;
revoke all on public.radar_data_cache from anon,authenticated;
grant select,insert,update on public.radar_data_cache to service_role;
create or replace function public.radar_claim_data(p_key text,p_seconds integer default 30) returns boolean
language plpgsql security definer set search_path=public as $$
begin
 if p_key !~ '^(quote|options|history):[A-Z0-9][A-Z0-9.-]{0,14}$' then raise exception 'Invalid cache key';end if;
 perform pg_advisory_xact_lock(703007);
 if exists(select 1 from radar_data_cache where id=p_key and (last_attempt>now()-make_interval(secs=>greatest(30,least(p_seconds,43200))) or lease_until>now())) then return false;end if;
 if (select count(*) from radar_data_cache where last_attempt>now()-interval '1 minute')>=20 then return false;end if;
 insert into radar_data_cache(id,last_attempt,lease_until) values(p_key,now(),now()+interval '25 seconds')
 on conflict(id) do update set last_attempt=now(),lease_until=now()+interval '25 seconds';return true;
end;$$;
revoke all on function public.radar_claim_data(text,integer) from public,anon,authenticated;
grant execute on function public.radar_claim_data(text,integer) to service_role;
create table if not exists public.radar_evaluations (
 id text primary key, snapshot_id uuid not null references radar_research_snapshots(id),
 created_at timestamptz not null default now(), payload jsonb not null
);
alter table public.radar_evaluations enable row level security;
revoke all on public.radar_evaluations from anon,authenticated;
grant select,insert on public.radar_evaluations to service_role;
drop trigger if exists radar_evaluation_immutable on public.radar_evaluations;
create trigger radar_evaluation_immutable before update or delete on public.radar_evaluations for each row execute function public.radar_snapshot_immutable();
-- Recover provider failures without suppressing retries for twelve hours.
create or replace function public.radar_claim_market(p_symbol text) returns boolean
language plpgsql security definer set search_path=public as $$
begin
 if not exists(select 1 from radar_universe where symbol=p_symbol and active) then return false;end if;
 perform pg_advisory_xact_lock(703005);
 if exists(select 1 from radar_market_cache where symbol=p_symbol and (lease_until>now() or
 last_attempt>now()-case when last_error is null then interval '12 hours' else interval '15 minutes' end)) then return false;end if;
 if (select count(*) from radar_market_cache where last_attempt>now()-interval '24 hours')>=40 and
 not exists(select 1 from radar_market_cache where symbol=p_symbol) then return false;end if;
 insert into radar_market_cache(symbol,last_attempt,lease_until) values(p_symbol,now(),now()+interval '2 minutes')
 on conflict(symbol) do update set last_attempt=now(),lease_until=now()+interval '2 minutes';return true;
end;$$;
create or replace function public.radar_commit_research(p_owner uuid,p_symbol text,p_snapshot jsonb) returns boolean
language plpgsql security definer set search_path=public as $$
begin
 perform 1 from radar_research_queue where symbol=p_symbol and owner=p_owner and lease_until>now() for update;
 if not found then return false;end if;
 if p_snapshot->>'symbol' is distinct from p_symbol then raise exception 'Snapshot identity mismatch';end if;
 insert into radar_research_snapshots(id,symbol,engine_version,payload,target,horizon_sessions,evaluation_status)
 values((p_snapshot->>'id')::uuid,p_symbol,p_snapshot->>'engine_version',p_snapshot->'payload','research_monitor',5,'pending_underlying_monitor')
 on conflict(id) do nothing;
 if not radar_finish_research(p_owner,p_symbol,null) then raise exception 'Research lease expired';end if;
 return true;
end;$$;
revoke all on function public.radar_commit_research(uuid,text,jsonb) from public,anon,authenticated;
grant execute on function public.radar_commit_research(uuid,text,jsonb) to service_role;
commit;
