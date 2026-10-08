-- Derived lookup cache; original immutable acquisition records remain authoritative.
create table if not exists public.market_history_series (
 symbol text primary key,
 days jsonb not null
);
alter table public.market_history_series enable row level security;
revoke all on public.market_history_series from anon,authenticated;
grant select,insert,update on public.market_history_series to service_role;
create table if not exists public.market_history_indexed_sessions (
 id text primary key references public.market_history_days(id)
);
alter table public.market_history_indexed_sessions enable row level security;
revoke all on public.market_history_indexed_sessions from anon,authenticated;
grant select,insert on public.market_history_indexed_sessions to service_role;
create or replace function public.radar_index_history(p_sessions date[])
returns integer language plpgsql security invoker set search_path=public as $$
declare affected integer;
begin
 if cardinality(p_sessions)>100 then raise exception 'Bounded sessions required'; end if;
 insert into public.market_history_series(symbol,days)
 select b.value->>'T',jsonb_object_agg(d.session_date::text,
  b.value || jsonb_build_object('archive_id',d.id))
 from public.market_history_days d
 cross join lateral jsonb_array_elements(d.payload->'results') b
 where d.feed='massive_daily_adjusted' and d.session_date=any(p_sessions)
 group by b.value->>'T'
 on conflict(symbol) do update set days=market_history_series.days || excluded.days;
 get diagnostics affected=row_count;
 insert into public.market_history_indexed_sessions(id)
 select id from public.market_history_days
 where feed='massive_daily_adjusted' and session_date=any(p_sessions)
 on conflict do nothing;
 return affected;
end $$;
revoke all on function public.radar_index_history(date[]) from public,anon,authenticated;
grant execute on function public.radar_index_history(date[]) to service_role;
create or replace function public.radar_history_packs(p_symbols text[],p_start date,p_end date)
returns table(session_date date,observed_at timestamptz,available_at timestamptz,
 source text,feed text,results jsonb)
language plpgsql security invoker set search_path=public as $$
begin
 if cardinality(p_symbols)>100 or p_end-p_start>430 or p_start>p_end then
  raise exception 'Bounded history range required';
 end if;
 return query
 select d.session_date,d.observed_at,d.available_at,d.source,d.feed,
 jsonb_agg(b.value-'archive_id' order by s.symbol)
 from public.market_history_series s
 cross join lateral jsonb_each(s.days) b
 join public.market_history_days d on d.id=b.value->>'archive_id'
 where s.symbol=any(p_symbols) and b.key::date between p_start and p_end
 and d.feed='massive_daily_adjusted'
 group by d.session_date,d.observed_at,d.available_at,d.source,d.feed
 order by d.session_date;
end $$;
revoke all on function public.radar_history_packs(text[],date,date) from public,anon,authenticated;
grant execute on function public.radar_history_packs(text[],date,date) to service_role;
