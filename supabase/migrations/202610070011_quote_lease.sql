begin;
create table public.quote_leases(symbol text primary key references public.securities(symbol), next_refresh timestamptz not null);
alter table public.quote_leases enable row level security;
grant all on public.quote_leases to service_role;
create or replace function public.radar_claim_quote(p_symbol text) returns boolean
language plpgsql security definer set search_path=public as $$
declare claimed text;
begin
 insert into quote_leases(symbol,next_refresh) values(p_symbol,now()+interval '15 seconds')
 on conflict(symbol) do update set next_refresh=now()+interval '15 seconds'
 where quote_leases.next_refresh<=now() returning symbol into claimed;
 return claimed is not null;
end $$;
revoke all on function public.radar_claim_quote(text) from public,anon,authenticated;
grant execute on function public.radar_claim_quote(text) to service_role;
commit;
