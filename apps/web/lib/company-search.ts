export function searchWords(term: string): string[] {
  return term
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length > 1);
}

export function matchesCompany(
  company: { symbol: string; name: string },
  term: string,
): boolean {
  const words = searchWords(term);
  if (!words.length) return false;
  const haystack = `${company.symbol} ${company.name}`.toLowerCase();
  return words.every((word) => haystack.includes(word));
}

export function narrowestWord(term: string): string {
  return searchWords(term).sort((a, b) => b.length - a.length)[0] ?? "";
}
