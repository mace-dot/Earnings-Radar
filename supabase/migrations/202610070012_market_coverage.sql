begin;
create table if not exists public.market_coverage (
 symbol text primary key references public.securities(symbol),
 state text not null default 'queued' check(state in ('queued','running','covered','unavailable','failed')),
 checked_at timestamptz, next_attempt_at timestamptz not null default now(),
 lease_until timestamptz, lease_token uuid, source text, feed text,
 last_session date, sample_size integer not null default 0, reason text,
 payload jsonb not null default '{}'
);
alter table public.market_coverage enable row level security;
revoke all on public.market_coverage from anon, authenticated;
grant all on public.market_coverage to service_role;
create index if not exists market_coverage_due_idx on public.market_coverage(next_attempt_at,checked_at);
create or replace function public.radar_claim_market(p_limit integer default 100)
returns setof public.market_coverage language plpgsql security definer set search_path=public as $$
begin
 insert into public.market_coverage(symbol) select symbol from public.securities where active on conflict do nothing;
 return query
 with wanted as (
  select c.symbol from public.market_coverage c join public.securities s using(symbol)
  where s.active and c.next_attempt_at<=now() and (c.lease_until is null or c.lease_until<now())
  order by c.checked_at asc nulls first,c.symbol asc
  for update of c skip locked limit greatest(1,least(p_limit,100))
 ) update public.market_coverage c set state='running',lease_until=now()+interval '15 minutes',lease_token=gen_random_uuid()
 from wanted w where c.symbol=w.symbol returning c.*;
end $$;
revoke all on function public.radar_claim_market(integer) from public, anon, authenticated;
grant execute on function public.radar_claim_market(integer) to service_role;
create or replace view public.market_coverage_summary with (security_invoker=true) as
select count(*) as total_identifiers,
 count(*) filter(where state='covered') as covered,
 count(*) filter(where state='covered' and checked_at>=now()-interval '36 hours') as recently_checked,
 count(*) filter(where state='unavailable') as unavailable,
 count(*) filter(where state='failed') as failed,
 count(*) filter(where state in ('queued','running')) as waiting,
 max(checked_at) as latest_check
from public.market_coverage;
revoke all on public.market_coverage_summary from anon,authenticated;
grant select on public.market_coverage_summary to service_role;
create or replace view public.latest_price_features with (security_invoker=true) as
select distinct on(symbol) id,symbol,as_of,values from public.features
where version in ('price-v1','market-scan-v1') order by symbol,as_of desc,id;
revoke all on public.latest_price_features from anon,authenticated;
grant select on public.latest_price_features to service_role;
commit;
