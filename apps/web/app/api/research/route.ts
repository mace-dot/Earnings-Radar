import { NextRequest, NextResponse } from "next/server";
import { sameOrigin } from "@/lib/same-origin";
export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  if (!sameOrigin(origin, request.url, request.headers.get("host")))
    return NextResponse.json(
      { error: "Same-origin request required" },
      { status: 403 },
    );
  const text = await request.text();
  if (text.length > 128)
    return NextResponse.json({ error: "Request too large" }, { status: 413 });
  let symbol: string;
  try {
    const body: unknown = JSON.parse(text);
    if (
      !body ||
      typeof body !== "object" ||
      !("symbol" in body) ||
      typeof body.symbol !== "string"
    )
      throw new Error();
    symbol = body.symbol.toUpperCase();
  } catch {
    return NextResponse.json({ error: "Invalid symbol" }, { status: 400 });
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
    const response = await fetch(`${base}/rest/v1/rpc/radar_request_score`, {
      method: "POST",
      headers,
      body: JSON.stringify({ p_symbol: symbol }),
      cache: "no-store",
      signal: AbortSignal.timeout(12000),
    });
    if (!response.ok)
      return NextResponse.json(
        { error: "Unable to request research" },
        { status: 503 },
      );
    return NextResponse.json({ state: await response.json() });
  } catch {
    return NextResponse.json(
      { error: "Collector request unavailable" },
      { status: 503 },
    );
  }
}
