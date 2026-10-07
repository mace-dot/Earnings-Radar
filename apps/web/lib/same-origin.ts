export function sameOrigin(
  origin: string | null,
  requestURL: string,
  host: string | null,
): boolean {
  if (!origin || !host) return false;
  try {
    const source = new URL(origin);
    const target = new URL(requestURL);
    target.host = host;
    return (
      source.origin === target.origin &&
      !source.username &&
      !source.password &&
      source.pathname === "/" &&
      !source.search &&
      !source.hash
    );
  } catch {
    return false;
  }
}
