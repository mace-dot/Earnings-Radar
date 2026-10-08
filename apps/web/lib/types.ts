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
  contract?: {
    contract: string;
    kind: string;
    strike: number;
    expiry: string;
    bid: number;
    ask: number;
    delta: number;
    cost: number;
    breakeven: number;
    quote_as_of: string;
    source: string;
    executable: boolean;
    deliverable_verified: boolean;
  };
  estimate?: {
    strike: number;
    expiry: string;
    debit_per_share: number;
    estimated_one_standard_contract_cost: number;
    lower_breakeven: number;
    upper_breakeven: number;
    multiplier_assumption: string;
    quote_kind: string;
    event_specific: boolean;
  } | null;
};
export type Side = {
  id: string;
  side: "BULL" | "BEAR" | "MORE" | "LESS";
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
  payload: {
    subtitle: string;
    favored: string | null;
    badges: string[];
    metrics?: {
      rv_10: number | null;
      rv_60: number | null;
      vol_compression_ratio: number | null;
      bb_width_percentile: number | null;
      move_meter: number | null;
    };
    option_estimate?: { implied_move: number | null } | null;
    source?: string;
  };
  sides: Side[];
};
export type Pick = {
  id: string;
  symbol: string;
  side: string;
  as_of: string;
  expires_at: string;
  payload: {
    line_kind?: string;
    tier?: string;
    entry?: number;
    feed?: string;
    status?: string;
    trade?: Trade;
    bullets?: string[];
    countercase?: string[];
    invalidation?: string;
    selection_rule?: string;
    grading_rule?: string;
  };
};
export type Outcome = {
  pick_id: string;
  graded_at: string;
  source: string;
  payload: {
    return_fraction?: number;
    result?: string;
    reason?: string;
    direction_result?: string;
    hypothetical_pnl?: number;
    hypothetical_return?: number;
    note?: string;
  };
};
