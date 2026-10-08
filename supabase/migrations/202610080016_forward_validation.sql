create table if not exists public.validation_cases (
 id text primary key,
 symbol text not null references public.securities(symbol),
 as_of timestamptz not null,
 session_date date not null,
 version text not null,
 payload jsonb not null
);
create table if not exists public.validation_outcomes (
 id text primary key references public.validation_cases(id),
 evaluated_at timestamptz not null,
 payload jsonb not null
);
create index if not exists validation_cases_cutoff on public.validation_cases(as_of);
alter table public.validation_cases enable row level security;
alter table public.validation_outcomes enable row level security;
revoke all on public.validation_cases,public.validation_outcomes from anon,authenticated;
grant select,insert on public.validation_cases,public.validation_outcomes to service_role;
drop trigger if exists validation_cases_immutable on public.validation_cases;
create trigger validation_cases_immutable before update or delete on public.validation_cases
 for each row execute function public.radar_snapshot_immutable();
drop trigger if exists validation_outcomes_immutable on public.validation_outcomes;
create trigger validation_outcomes_immutable before update or delete on public.validation_outcomes
 for each row execute function public.radar_snapshot_immutable();
