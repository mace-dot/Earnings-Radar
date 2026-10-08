import { NextRequest, NextResponse } from "next/server";
import { historyAuthorized, historyRequest } from "@/lib/history-relay";

export const runtime = "nodejs";
export const maxDuration = 30;

// Authenticated, bounded source retrieval only. Scoring stays in the Python worker.
export async function POST(request: NextRequest) {
  const body = await request.text();
  if (body.length > 256)
    return NextResponse.json({ error: "Request too large" }, { status: 413 });
  if (
    !historyAuthorized(
      process.env.SUPABASE_SERVICE_ROLE_KEY ?? "",
      request.headers.get("x-radar-timestamp"),
      request.headers.get("x-radar-signature"),
      body,
    )
  )
    return NextResponse.json(
      { error: "Worker authentication required" },
      { status: 401 },
    );
  let input;
  try {
    input = historyRequest(JSON.parse(body));
  } catch {
    input = null;
  }
  if (!input)
    return NextResponse.json(
      { error: "Invalid bounded history request" },
      { status: 400 },
    );
  const query = new URLSearchParams({
    assetclass: "stocks",
    fromdate: input.start,
    todate: input.end,
    limit: "5000",
  });
  try {
    const response = await fetch(
      `https://api.nasdaq.com/api/quote/${input.symbol}/historical?${query}`,
      {
        headers: { "User-Agent": "EarningsRadar/1.0 contact mace@udel.edu" },
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(15000),
      },
    );
    if (!response.ok)
      return NextResponse.json(
        { error: "Source request failed", upstream_status: response.status },
        { status: 502 },
      );
    const text = await response.text();
    if (text.length > 2000000) throw new Error("Source response exceeds bound");
    const data: unknown = JSON.parse(text);
    return NextResponse.json(
      { data, retrieved_at: new Date().toISOString(), source: "Nasdaq" },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return NextResponse.json(
      { error: "Source history unavailable" },
      { status: 503 },
    );
  }
}
