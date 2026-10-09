export type SavedEarning = {
  period: string;
  as_of: string;
  payload: {
    reported_date?: string | null;
    reported_eps?: number | null;
    estimated_eps?: number | null;
  };
};

export function describeSurprise(row: SavedEarning): string {
  const reported = row.payload.reported_eps;
  const estimate = row.payload.estimated_eps;
  const when = row.payload.reported_date ?? row.period;
  if (reported == null) {
    return `The quarter ending ${row.period} has no reported profit figure in the saved history.`;
  }
  if (estimate == null) {
    return `On ${when}, the saved history shows a reported profit of ${reported}. No estimate was included with that report.`;
  }
  const comparison =
    reported > estimate
      ? "above"
      : reported < estimate
        ? "below"
        : "the same as";
  return `On ${when}, the company reported ${reported}, ${comparison} the ${estimate} estimate. This describes a past report.`;
}
