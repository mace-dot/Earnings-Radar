-- A market-wide day updates ~12,500 accumulated symbol histories. Production
-- EXPLAIN ANALYZE measured 14.9s, exceeding PostgREST's inherited 8s timeout.
-- Scope the allowance to this service-role-only RPC, below the client's 45s.
alter function public.radar_index_history(date[]) set statement_timeout = '40s';
notify pgrst, 'reload schema';
