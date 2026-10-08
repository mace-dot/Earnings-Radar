import type { Bar } from "@/lib/types";

export function selectHistory(stored: Bar[], coverage: Bar[]): Bar[] {
  const series = new Map<string, Map<string, Bar>>();
  for (const bar of [...coverage, ...stored]) {
    if (!Number.isFinite(Number(bar.close)) || Number(bar.close) <= 0) continue;
    const identity = `${bar.source}:${bar.feed}`;
    const days = series.get(identity) ?? new Map<string, Bar>();
    const old = days.get(bar.session_date);
    if (!old || (bar.available_at ?? "") > (old.available_at ?? ""))
      days.set(bar.session_date, bar);
    series.set(identity, days);
  }
  const candidates = [...series.values()].map((days) =>
    [...days.values()].sort((a, b) =>
      a.session_date.localeCompare(b.session_date),
    ),
  );
  candidates.sort((a, b) => {
    const aAdjusted = a.length >= 60 && a[0].feed === "massive_daily_adjusted";
    const bAdjusted = b.length >= 60 && b[0].feed === "massive_daily_adjusted";
    if (aAdjusted !== bAdjusted) return aAdjusted ? -1 : 1;
    const completeA = a.length >= 60,
      completeB = b.length >= 60;
    if (completeA !== completeB) return completeA ? -1 : 1;
    return (
      (b.at(-1)?.session_date ?? "").localeCompare(
        a.at(-1)?.session_date ?? "",
      ) || b.length - a.length
    );
  });
  return (candidates[0] ?? []).slice(-252);
}
