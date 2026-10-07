begin;
create table if not exists public.radar_model_registry (
 id text primary key,created_at timestamptz not null default now(),
 status text not null default 'draft' check(status in ('draft','review_required','rejected','retired')),
 payload jsonb not null,
 check(coalesce((payload->>'live_forecasts_enabled')::boolean,false)=false)
);
alter table public.radar_model_registry enable row level security;
revoke all on public.radar_model_registry from anon,authenticated;
grant select,insert on public.radar_model_registry to service_role;
-- Approval/activation is deliberately absent: evaluation cannot self-promote a model.
drop trigger if exists radar_model_report_immutable on public.radar_model_registry;
create trigger radar_model_report_immutable before update or delete on public.radar_model_registry for each row execute function public.radar_snapshot_immutable();
commit;
