begin;
create table if not exists public.radar_market_cache (
 symbol text primary key references public.radar_universe(symbol),
 payload jsonb not null default '{}',updated_at timestamptz not null default now(),
 last_attempt timestamptz,last_error text,lease_until timestamptz
);
alter table public.radar_market_cache enable row level security;
revoke all on public.radar_market_cache from anon,authenticated;
grant select,insert,update on public.radar_market_cache to service_role;
create or replace function public.radar_claim_market(p_symbol text) returns boolean
language plpgsql security definer set search_path=public as $$
begin
 if not exists(select 1 from radar_universe where symbol=p_symbol and active) then return false;end if;
 perform pg_advisory_xact_lock(703005);
 if exists(select 1 from radar_market_cache where symbol=p_symbol and (last_attempt>now()-interval '12 hours' or lease_until>now())) then return false;end if;
 if (select count(*) from radar_market_cache where last_attempt>now()-interval '24 hours')>=40 then return false;end if;
 insert into radar_market_cache(symbol,last_attempt,lease_until) values(p_symbol,now(),now()+interval '2 minutes')
 on conflict(symbol) do update set last_attempt=now(),lease_until=now()+interval '2 minutes';
 return true;
end;$$;
revoke all on function public.radar_claim_market(text) from public,anon,authenticated;
grant execute on function public.radar_claim_market(text) to service_role;
alter table public.radar_market_cache add column if not exists news_attempt timestamptz;
alter table public.radar_market_cache add column if not exists news_status jsonb not null default '[]';
create or replace function public.radar_claim_news(p_symbol text) returns boolean
language plpgsql security definer set search_path=public as $$
begin
 if not exists(select 1 from radar_universe where symbol=p_symbol and active) then return false;end if;
 perform pg_advisory_xact_lock(703006);
 if exists(select 1 from radar_market_cache where symbol=p_symbol and news_attempt>now()-interval '12 hours') then return false;end if;
 if (select count(*) from radar_market_cache where news_attempt>now()-interval '24 hours')>=40 then return false;end if;
 insert into radar_market_cache(symbol,news_attempt) values(p_symbol,now()) on conflict(symbol) do update set news_attempt=now();
 return true;
end;$$;
revoke all on function public.radar_claim_news(text) from public,anon,authenticated;
grant execute on function public.radar_claim_news(text) to service_role;
commit;
