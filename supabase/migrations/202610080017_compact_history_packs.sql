-- Share parent provenance once per session instead of once per symbol/bar.
create or replace function public.radar_history_packs(p_symbols text[],p_start date,p_end date)
returns table(session_date date, observed_at timestamptz, available_at timestamptz,
 source text, feed text, results jsonb)
language plpgsql security invoker set search_path=public as $$
begin
 if cardinality(p_symbols) > 100 or p_end-p_start > 430 or p_start > p_end then
  raise exception 'Bounded history range required';
 end if;
 return query
 select d.session_date,d.observed_at,d.available_at,d.source,d.feed,
 jsonb_agg(b.value order by b.value->>'T')
 from public.market_history_days d
 cross join lateral jsonb_array_elements(d.payload->'results') b
 where d.feed='massive_daily_adjusted' and d.session_date between p_start and p_end
 and b.value->>'T'=any(p_symbols)
 group by d.session_date,d.observed_at,d.available_at,d.source,d.feed
 order by d.session_date;
end $$;
revoke all on function public.radar_history_packs(text[],date,date) from public,anon,authenticated;
grant execute on function public.radar_history_packs(text[],date,date) to service_role;
