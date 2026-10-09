import "server-only";
const allowed = new Set([
  "securities",
  "earnings_events",
  "daily_bars",
  "lines",
  "line_sides",
  "picks",
  "pick_outcomes",
  "engine_runs",
  "news_items",
  "model_registry",
  "market_observations",
  "forum_posts",
  "features",
  "market_coverage_summary",
  "latest_price_features",
  "market_coverage",
  "estimate_revisions",
]);
export async function read<T>(
  table: string,
  query: Record<string, string> = {},
  fresh = false,
): Promise<T[]> {
  if (!allowed.has(table)) throw new Error("Unsupported data request");
  const base = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!base || !key || !/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(base))
    throw new Error("Database connection unavailable");
  const headers: Record<string, string> = { apikey: key };
  if (!key.startsWith("sb_secret_")) headers.Authorization = `Bearer ${key}`;
  const response = await fetch(
    `${base}/rest/v1/${table}?${new URLSearchParams({ select: "*", limit: "100", ...query })}`,
    {
      headers,
      ...(fresh
        ? { cache: "no-store" as const }
        : { next: { revalidate: 60 } }),
      signal: AbortSignal.timeout(12000),
    },
  );
  if (!response.ok) throw new Error("Database request unavailable");
  return response.json() as Promise<T[]>;
}
