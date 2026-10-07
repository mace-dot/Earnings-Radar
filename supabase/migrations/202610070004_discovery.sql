begin;
create table if not exists public.radar_universe (
 symbol text primary key check(symbol ~ '^[A-Z0-9][A-Z0-9.-]{0,14}$'),
 cik text not null check(cik ~ '^[0-9]{10}$'), name text not null,
 exchange text, active boolean not null default true,
 aliases jsonb not null default '[]', retrieved_at timestamptz not null,
 source_url text not null default 'https://www.sec.gov/files/company_tickers_exchange.json'
);
create index if not exists radar_universe_cik on public.radar_universe(cik);
create table if not exists public.radar_research_queue (
 symbol text primary key references public.radar_universe(symbol),
 reason text not null check(reason in ('search','filing','watchlist','rotation')),
 priority integer not null default 0, status text not null default 'queued',
 requested_at timestamptz not null default now(), next_attempt timestamptz not null default now(),
 last_success timestamptz, attempts integer not null default 0,
 owner uuid, lease_until timestamptz, last_error text
);
create table if not exists public.radar_research_snapshots (
 id uuid primary key default gen_random_uuid(),symbol text not null,created_at timestamptz not null default now(),
 engine_version text not null,payload jsonb not null,
 target text not null default 'research_monitor', horizon_sessions integer not null default 5,
 evaluation_status text not null default 'market_data_unavailable'
);
create index if not exists radar_snapshot_time on public.radar_research_snapshots(created_at desc);
create table if not exists public.radar_model_usage(day date primary key,calls integer not null default 0);
create table if not exists public.radar_model_cache(id text primary key,payload jsonb not null,created_at timestamptz not null default now());
alter table public.radar_universe enable row level security;
alter table public.radar_research_queue enable row level security;
alter table public.radar_research_snapshots enable row level security;
alter table public.radar_model_usage enable row level security;
alter table public.radar_model_cache enable row level security;
revoke all on public.radar_universe,public.radar_research_queue,public.radar_research_snapshots,public.radar_model_usage,public.radar_model_cache from anon,authenticated;
grant select,insert,update on public.radar_universe,public.radar_research_queue,public.radar_model_usage,public.radar_model_cache to service_role;
grant select,insert on public.radar_research_snapshots to service_role;
create or replace function public.radar_snapshot_immutable() returns trigger language plpgsql as $$begin raise exception 'Research snapshots are immutable';end;$$;
drop trigger if exists radar_snapshot_immutable on public.radar_research_snapshots;
create trigger radar_snapshot_immutable before update or delete on public.radar_research_snapshots for each row execute function public.radar_snapshot_immutable();

create or replace function public.radar_enqueue(p_symbol text,p_reason text default 'search',p_priority integer default 50)
returns jsonb language plpgsql security definer set search_path=public as $$
declare existing public.radar_research_queue;begin
 if p_reason not in ('search','filing','watchlist','rotation') then raise exception 'Unknown reason';end if;
 if not exists(select 1 from public.radar_universe where symbol=p_symbol and active) then raise exception 'Unsupported company';end if;
 perform pg_advisory_xact_lock(703004);
 select * into existing from public.radar_research_queue where symbol=p_symbol;
 if found and (existing.status in ('queued','running','retry') or existing.last_success>now()-interval '24 hours') then return to_jsonb(existing);end if;
 if (select count(*) from public.radar_research_queue where requested_at>now()-interval '24 hours')>=40 then return jsonb_build_object('status','daily_capacity','symbol',p_symbol);end if;
 insert into public.radar_research_queue(symbol,reason,priority) values(p_symbol,p_reason,least(100,greatest(0,p_priority)))
 on conflict(symbol) do update set reason=excluded.reason,priority=excluded.priority,status='queued',requested_at=now(),next_attempt=now(),attempts=0,last_error=null;
 select * into existing from public.radar_research_queue where symbol=p_symbol;return to_jsonb(existing);
end;$$;

create or replace function public.radar_claim_research(p_owner uuid,p_symbol text default null)
returns jsonb language plpgsql security definer set search_path=public as $$
declare item public.radar_research_queue;begin
 update public.radar_research_queue set status='failed',last_error='Research retry limit reached after expired lease',owner=null,lease_until=null where status='running' and lease_until<now() and attempts>=5;
 select * into item from public.radar_research_queue where (p_symbol is null or symbol=p_symbol)
 and (status in ('queued','retry') or status='running' and lease_until<now()) and attempts<5 and next_attempt<=now()
 order by priority desc,requested_at asc for update skip locked limit 1;
 if not found then return null;end if;
 update public.radar_collection_state set owner=p_owner,lease_until=now()+interval '5 minutes',last_started=now()
 where id=true and (lease_until is null or lease_until<now());
 if not found then return null;end if;
 update public.radar_research_queue set owner=p_owner,lease_until=now()+interval '5 minutes',status='running',attempts=attempts+1 where symbol=item.symbol;
 update public.radar_research_queue set status='failed',last_error='Research retry limit reached after expired lease',owner=null,lease_until=null where status='running' and lease_until<now() and attempts>=5;
 select * into item from public.radar_research_queue where symbol=item.symbol;return to_jsonb(item);
end;$$;

create or replace function public.radar_finish_research(p_owner uuid,p_symbol text,p_error text default null)
returns boolean language plpgsql security definer set search_path=public as $$
begin
 update public.radar_research_queue set status=case when p_error is null then 'complete' when attempts>=5 then 'failed' else 'retry' end,
 last_success=case when p_error is null then now() else last_success end,last_error=p_error,
 next_attempt=now()+make_interval(secs=>least(3600,(power(2,attempts)*60)::int)),lease_until=null,owner=null
 where symbol=p_symbol and owner=p_owner and lease_until>now();
 if not found then return false;end if;
 update public.radar_collection_state set lease_until=null,last_finished=now(),last_error=p_error where id=true and owner=p_owner;
 return true;
end;$$;

create or replace function public.radar_reserve_model_call() returns boolean
language plpgsql security definer set search_path=public as $$
begin
 insert into public.radar_model_usage(day,calls) values(current_date,1)
 on conflict(day) do update set calls=radar_model_usage.calls+1 where radar_model_usage.calls<10;
 return found;
end;$$;
revoke all on function public.radar_enqueue(text,text,integer),public.radar_claim_research(uuid,text),public.radar_finish_research(uuid,text,text),public.radar_reserve_model_call() from public,anon,authenticated;
grant execute on function public.radar_enqueue(text,text,integer),public.radar_claim_research(uuid,text),public.radar_finish_research(uuid,text,text),public.radar_reserve_model_call() to service_role;
create or replace function public.radar_search_directory(p_query text) returns jsonb
language sql security definer set search_path=public as $$
 select coalesce(jsonb_agg(to_jsonb(x)),'[]'::jsonb) from (
 select symbol,cik,name,exchange,active,retrieved_at from public.radar_universe
 where length(trim(p_query)) between 1 and 60 and (symbol ilike '%'||p_query||'%' or name ilike '%'||p_query||'%' or cik=p_query
 or exists(select 1 from jsonb_array_elements_text(aliases) a where a ilike '%'||p_query||'%'))
 order by active desc,case when lower(symbol)=lower(p_query) then 0 when symbol ilike p_query||'%' then 1 else 2 end,symbol limit 15) x;
$$;
revoke all on function public.radar_search_directory(text) from public,anon,authenticated;
grant execute on function public.radar_search_directory(text) to service_role;

commit;
