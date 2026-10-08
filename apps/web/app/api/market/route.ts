import { NextRequest, NextResponse } from "next/server";
import { sameOrigin } from "@/lib/same-origin";
import { read } from "@/lib/db";
import type { Market } from "@/components/context";
export async function POST(request: NextRequest) {
  if (
    !sameOrigin(
      request.headers.get("origin"),
      request.url,
      request.headers.get("host"),
    )
  )
    return NextResponse.json(
      { error: "Same-origin request required" },
      { status: 403 },
    );
  const text = await request.text();
  if (text.length > 128)
    return NextResponse.json({ error: "Request too large" }, { status: 413 });
  let symbol: string;
  try {
    const data: unknown = JSON.parse(text);
    if (
      !data ||
      typeof data !== "object" ||
      !("symbol" in data) ||
      typeof data.symbol !== "string"
    )
      throw new Error();
    symbol = data.symbol.toUpperCase();
  } catch {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
  if (!/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(symbol))
    return NextResponse.json({ error: "Invalid symbol" }, { status: 400 });
  const base = process.env.SUPABASE_URL,
    key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!base || !key)
    return NextResponse.json(
      { error: "Database unavailable" },
      { status: 503 },
    );
  const headers: Record<string, string> = {
    apikey: key,
    "Content-Type": "application/json",
  };
  if (!key.startsWith("sb_secret_")) headers.Authorization = `Bearer ${key}`;
  try {
    const known = await read(
      "securities",
      {
        symbol: `eq.${symbol}`,
        select: "symbol",
        limit: "1",
      },
      true,
    );
    if (!known.length)
      return NextResponse.json({ error: "Unknown symbol" }, { status: 404 });
    const previous = await read<Market>(
      "market_observations",
      {
        symbol: `eq.${symbol}`,
        feed: "in.(iex,finnhub_free)",
        order: "retrieved_at.desc",
        limit: "1",
      },
      true,
    );
    const claim = await fetch(`${base}/rest/v1/rpc/radar_claim_quote`, {
      method: "POST",
      headers,
      body: JSON.stringify({ p_symbol: symbol }),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!claim.ok) throw new Error();
    if (!(await claim.json())) {
      const trade = previous[0]?.payload.latestTrade;
      return NextResponse.json(
        trade
          ? {
              price: trade.p,
              as_of: trade.t,
              feed: previous[0]?.source ?? previous[0]?.feed,
              cached: true,
            }
          : { error: "Refresh already in progress" },
        { status: trade ? 200 : 202 },
      );
    }
    const apiKey = process.env.FINNHUB_API_KEY ?? process.env.FINN_HUB;
    if (!apiKey)
      return NextResponse.json(
        { error: "Finnhub quote credential unavailable" },
        { status: 503 },
      );
    const response = await fetch(
      `https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(symbol)}`,
      {
        headers: { "X-Finnhub-Token": apiKey },
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      },
    );
    if (!response.ok)
      return NextResponse.json(
        { error: "Quote provider temporarily unavailable" },
        { status: 503 },
      );
    const data = await response.json();
    if (
      typeof data.c !== "number" ||
      !Number.isFinite(data.c) ||
      data.c <= 0 ||
      typeof data.t !== "number" ||
      data.t <= 0
    )
      throw new Error();
    const trade = { p: data.c, t: new Date(data.t * 1000).toISOString() };
    const now = new Date().toISOString();
    if (Date.parse(trade.t) > Date.now() + 1000) throw new Error();
    const saved = await fetch(
      `${base}/rest/v1/market_observations?on_conflict=id`,
      {
        method: "POST",
        headers: {
          ...headers,
          Prefer: "resolution=merge-duplicates,return=minimal",
        },
        body: JSON.stringify([
          {
            id: `${symbol}:latest:finnhub`,
            symbol,
            source: "Finnhub",
            feed: "finnhub_free",
            observed_at: trade.t,
            retrieved_at: now,
            payload: {
              ...previous[0]?.payload,
              latestTrade: trade,
              price_source: "Finnhub",
            },
          },
        ]),
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      },
    );
    if (!saved.ok) throw new Error();
    return NextResponse.json({
      price: trade.p,
      as_of: trade.t,
      feed: "Finnhub",
      retrieved_at: now,
      cached: false,
    });
  } catch {
    return NextResponse.json(
      { error: "Market refresh unavailable" },
      { status: 503 },
    );
  }
}
