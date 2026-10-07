const hosts = new Set([
  "benzinga.com",
  "reuters.com",
  "cnbc.com",
  "finance.yahoo.com",
  "marketwatch.com",
  "wsj.com",
  "bloomberg.com",
  "sec.gov",
  "seekingalpha.com",
  "stocktwits.com",
  "investors.micron.com",
]);
export function sourceURL(input: string): string | null {
  try {
    const url = new URL(input);
    const host = url.hostname.replace(/^www\./, "");
    return url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      hosts.has(host)
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}
