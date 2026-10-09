export type BoardEvent = { symbol: string; report_date: string };
export type BoardPick = { symbol: string };

export function addDays(day: string, days: number): string {
  const date = new Date(`${day}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function chooseBoard(
  events: BoardEvent[],
  picks: BoardPick[],
  today: string,
  view: string,
) {
  const upcoming = events
    .filter((event) => event.report_date >= today)
    .sort((a, b) => a.report_date.localeCompare(b.report_date));
  const weekEnd = addDays(today, 7);
  const thisWeek = upcoming.filter((event) => event.report_date <= weekEnd);
  const calendar = thisWeek.length ? thisWeek : upcoming;
  const radarSymbols = [...new Set(picks.map((pick) => pick.symbol))];
  const earningsSymbols = [...new Set(calendar.map((event) => event.symbol))];
  const mode: "earnings" | "radar" =
    view === "earnings" || radarSymbols.length === 0 ? "earnings" : "radar";
  return {
    mode,
    symbols: mode === "earnings" ? earningsSymbols : radarSymbols,
    calendarConnected: upcoming.length > 0,
    earningsLabel: thisWeek.length
      ? "Earnings this week"
      : "Next saved reports",
  };
}
