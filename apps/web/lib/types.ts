export type Security = {
  symbol: string;
  name: string;
  sector: string;
  exchange: string;
  source: string;
  as_of: string;
  asset_type: string;
};
export type Bar = {
  session_date: string;
  close: number;
  source: string;
  feed: string;
  available_at: string;
  as_of: string;
};
export type Event = {
  id: string;
  symbol: string;
  report_date: string;
  timing: string;
  date_status: string;
  as_of: string;
};
export type Trade = {
  instrument: string;
  explanation: string;
  entry: number | null;
  stop: number | null;
  max_loss: number | null;
  exit: string;
  missing: string[];
};
export type Side = {
  id: string;
  side: "BULL" | "BEAR";
  as_of: string;
  payload: {
    tier: string;
    sample_size: number;
    probability: number | null;
    bullets: string[];
    countercase: string[];
    invalidation: string;
    trade: Trade;
    badges: string[];
    score: number;
  };
};
export type Line = {
  id: string;
  symbol: string;
  kind: string;
  as_of: string;
  payload: { subtitle: string; favored: string | null; badges: string[] };
  sides: Side[];
};
export type Pick = {
  id: string;
  symbol: string;
  side: string;
  as_of: string;
  payload: { line_kind?: string; tier?: string; entry?: number; feed?: string };
};
export type Outcome = {
  pick_id: string;
  graded_at: string;
  payload: { return_fraction?: number; result?: string; reason?: string };
};
