import { formatAsOf } from "@/lib/time";
import { describeSurprise, type SavedEarning } from "@/lib/earnings-history";

export function EarningsHistory({
  rows,
  waiting,
}: {
  rows: SavedEarning[];
  waiting: boolean;
}) {
  if (!rows.length && !waiting) return null;
  const recent = [...rows].sort((a, b) =>
    (b.payload.reported_date ?? b.period).localeCompare(
      a.payload.reported_date ?? a.period,
    ),
  );
  return (
    <section className="panel">
      <h2>Past reports versus estimates</h2>
      {recent.length ? (
        recent.slice(0, 4).map((row) => (
          <p key={row.period}>
            {describeSurprise(row)}{" "}
            <small>Saved {formatAsOf(row.as_of)}.</small>
          </p>
        ))
      ) : (
        <p>
          Past earnings versus estimates have not been saved for this company
          yet. The daily scan saves a limited number of upcoming reports.
        </p>
      )}
    </section>
  );
}
