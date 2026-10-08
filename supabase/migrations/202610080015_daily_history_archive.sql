-- One immutable adjusted market-wide daily response per session.
create table if not exists public.market_history_days (
 id text primary key,
 session_date date not null,
 source text not null,
 feed text not null,
 observed_at timestamptz not null,
 available_at timestamptz not null,
 payload jsonb not null,
 check (available_at >= observed_at),
 unique(session_date,source,feed)
);
alter table public.market_history_days enable row level security;
revoke all on public.market_history_days from anon,authenticated;
grant select,insert on public.market_history_days to service_role;
create or replace function public.radar_history_bars(p_symbols text[],p_start date,p_end date)
returns table(symbol text, session_date date, observed_at timestamptz, available_at timestamptz,
 source text, feed text, open numeric,high numeric,low numeric,close numeric,volume bigint)
language plpgsql security invoker set search_path=public as $$
begin
 if cardinality(p_symbols) > 100 or p_end-p_start > 430 or p_start > p_end then
  raise exception 'Bounded history range required';
 end if;
 return query
 select b."T",d.session_date,d.observed_at,d.available_at,d.source,d.feed,
 b.o,b.h,b.l,b.c,b.v
 from public.market_history_days d
 cross join lateral jsonb_to_recordset(d.payload->'results')
 as b("T" text,o numeric,h numeric,l numeric,c numeric,v bigint)
 where d.feed='massive_daily_adjusted' and d.session_date between p_start and p_end and b."T"=any(p_symbols)
 order by b."T",d.session_date;
end $$;
revoke all on function public.radar_history_bars(text[],date,date) from public,anon,authenticated;
grant execute on function public.radar_history_bars(text[],date,date) to service_role;
