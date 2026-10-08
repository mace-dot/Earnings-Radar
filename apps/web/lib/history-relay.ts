import { createHmac, timingSafeEqual } from "node:crypto";
export function historySignature(key: string, timestamp: string, body: string) {
  return createHmac("sha256", key)
    .update(`earnings-radar-history-v1\n${timestamp}\n${body}`)
    .digest("hex");
}
export function historyAuthorized(
  key: string,
  timestamp: string | null,
  signature: string | null,
  body: string,
  now = Date.now(),
) {
  if (!key || !timestamp || !signature || !/^\d{10}$/.test(timestamp))
    return false;
  if (
    Math.abs(now / 1000 - Number(timestamp)) > 120 ||
    !/^[a-f0-9]{64}$/.test(signature)
  )
    return false;
  return timingSafeEqual(
    Buffer.from(historySignature(key, timestamp, body), "hex"),
    Buffer.from(signature, "hex"),
  );
}
export function historyRequest(
  value: unknown,
): { symbol: string; start: string; end: string } | null {
  if (!value || typeof value !== "object") return null;
  const data = value as Record<string, unknown>;
  if (
    typeof data.symbol !== "string" ||
    !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(data.symbol) ||
    typeof data.start !== "string" ||
    typeof data.end !== "string"
  )
    return null;
  const validDate = (text: string) =>
    /^\d{4}-\d{2}-\d{2}$/.test(text) &&
    Number.isFinite(Date.parse(text)) &&
    new Date(text).toISOString().slice(0, 10) === text;
  if (!validDate(data.start) || !validDate(data.end)) return null;
  const days = (Date.parse(data.end) - Date.parse(data.start)) / 86400000;
  if (days < 0 || days > 430) return null;
  return { symbol: data.symbol, start: data.start, end: data.end };
}
