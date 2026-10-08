begin;
-- Derive provenance from stored observations only. Never replace the old cutoff
-- with now(), or use an observation unavailable at the feature's original cutoff.
with observed as (
 select f.id, max((o->>'observed_at')::timestamptz) as last_observed
 from public.features f join public.market_coverage c using(symbol)
 cross join lateral jsonb_array_elements(c.payload->'observations') o
 where f.version='market-scan-v1' and not (f.values ? 'source_last_observed_at')
 and (o->>'observed_at')::timestamptz<=f.as_of
 and (o->>'available_at')::timestamptz<=f.as_of
 group by f.id
)
update public.features f set values=f.values||jsonb_build_object('source_last_observed_at',o.last_observed)
from observed o where f.id=o.id;
with observed as (
 select f.id,max(b.as_of) as last_observed
 from public.features f cross join lateral jsonb_array_elements_text(f.observations) observation_id
 join public.daily_bars b on b.id=observation_id
 where f.version='price-v1' and not (f.values ? 'source_last_observed_at')
 and b.as_of<=f.as_of and b.available_at<=f.as_of group by f.id
)
update public.features f set values=f.values||jsonb_build_object('source_last_observed_at',o.last_observed)
from observed o where f.id=o.id;
commit;
