-- Forward validation reads immutable feature identities and observation references.
create or replace view public.latest_price_features with (security_invoker=true) as
select distinct on(symbol) id,symbol,as_of,values,version,observations from public.features
where version in ('price-v1','market-scan-v1') order by symbol,as_of desc,id;
revoke all on public.latest_price_features from anon,authenticated;
grant select on public.latest_price_features to service_role;
