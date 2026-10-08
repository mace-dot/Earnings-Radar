begin;
alter table public.securities add column if not exists listing_metadata jsonb not null default '{}';
commit;
