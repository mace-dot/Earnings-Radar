begin;
create table public.score_queue (
 symbol text primary key references public.securities(symbol),
 state text not null default 'queued' check(state in ('queued','running','completed','failed')),
 requested_at timestamptz not null default now(), leased_until timestamptz,
 attempts int not null default 0, completed_at timestamptz, reason text
);
alter table public.score_queue enable row level security;
grant all on public.score_queue to service_role;
create table public.market_observations (
 id text primary key, symbol text not null references public.securities(symbol),
 source text not null, feed text not null, observed_at timestamptz not null,
 retrieved_at timestamptz not null, payload jsonb not null
);
alter table public.market_observations enable row level security;
grant all on public.market_observations to service_role;
create table public.forum_posts (
 id text primary key, symbol text not null references public.securities(symbol),
 source text not null, published_at timestamptz not null,
 retrieved_at timestamptz not null, payload jsonb not null
);
alter table public.forum_posts enable row level security;
grant all on public.forum_posts to service_role;
create or replace function public.radar_request_score(p_symbol text) returns text
language plpgsql security definer set search_path=public as $$
declare previous public.score_queue;
begin
 if not exists(select 1 from securities where symbol=p_symbol and active) then
  raise exception 'Unknown active symbol';
 end if;
 select * into previous from score_queue where symbol=p_symbol;
 if found and (previous.state in ('queued','running') or previous.requested_at>now()-interval '30 minutes') then
  return previous.state;
 end if;
 if (select count(*) from score_queue where requested_at>now()-interval '1 day')>=500 then
  return 'capacity';
 end if;
 insert into score_queue(symbol) values(p_symbol)
 on conflict(symbol) do update set state='queued', requested_at=now(), attempts=0, reason=null;
 return 'queued';
end $$;
create or replace function public.radar_claim_scores(p_limit int default 10) returns setof public.score_queue
language plpgsql security definer set search_path=public as $$
begin
 return query with candidates as (
 select symbol from score_queue where (state='queued' or state='running' and leased_until<now()) and attempts<3
 order by requested_at for update skip locked limit least(greatest(p_limit,1),100)
 ) update score_queue q set state='running', attempts=q.attempts+1, leased_until=now()+interval '15 minutes'
 from candidates c where q.symbol=c.symbol returning q.*;
end $$;
revoke all on function public.radar_request_score(text) from public,anon,authenticated;
revoke all on function public.radar_claim_scores(int) from public,anon,authenticated;
grant execute on function public.radar_request_score(text) to service_role;
grant execute on function public.radar_claim_scores(int) to service_role;
commit;
