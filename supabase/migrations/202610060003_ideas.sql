begin;
create table if not exists public.radar_ideas (
 user_id uuid not null references auth.users(id) on delete cascade,
 symbol text not null check(symbol ~ '^[A-Z][A-Z0-9.-]{0,9}$'),
 direction text not null check(direction in ('up','down')),
 evidence_id text not null references public.radar_events(id),
 created_at timestamptz not null default now(),
 primary key(user_id,symbol,direction)
);
alter table public.radar_ideas enable row level security;
drop policy if exists own_ideas on public.radar_ideas;
create policy own_ideas on public.radar_ideas for all to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
revoke all on public.radar_ideas from anon;
grant select,insert,update,delete on public.radar_ideas to authenticated,service_role;
-- Enforce the per-account cap even for direct authenticated database clients.
create or replace function public.radar_idea_limit() returns trigger language plpgsql set search_path=public as $$
begin
 perform pg_advisory_xact_lock(hashtextextended(new.user_id::text,1));
 if not exists(select 1 from public.radar_ideas where user_id=new.user_id and symbol=new.symbol and direction=new.direction)
 and (select count(*) from public.radar_ideas where user_id=new.user_id)>=20 then
 raise exception 'Keep up to 20 research ideas'; end if;
 return new;
end; $$;
drop trigger if exists radar_idea_limit on public.radar_ideas;
create trigger radar_idea_limit before insert on public.radar_ideas for each row execute function public.radar_idea_limit();

commit;
