import { formatAsOf } from "@/lib/time";
import type { Bar } from "@/lib/types";
export function PriceChart({ bars }: { bars: Bar[] }) {
  if (bars.length < 2)
    return (
      <div className="notice">
        Price history has not been collected for this company yet.
      </div>
    );
  const values = bars.map((b) => Number(b.close));
  const low = Math.min(...values),
    high = Math.max(...values),
    spread = high - low || 1;
  const points = values
    .map(
      (value, index) =>
        `${30 + (index / (values.length - 1)) * 740},${180 - ((value - low) / spread) * 150}`,
    )
    .join(" ");
  return (
    <figure>
      <svg
        viewBox="0 0 800 220"
        className="chart"
        role="img"
        aria-label={`Closing price history from ${bars[0].session_date} to ${bars.at(-1)?.session_date}; ${values.length} daily closes`}
      >
        <line
          x1="30"
          y1="190"
          x2="770"
          y2="190"
          stroke="currentColor"
          opacity=".3"
        />
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          points={points}
        />
        <text x="30" y="210">
          {bars[0].session_date}
        </text>
        <text x="675" y="210">
          {bars.at(-1)?.session_date}
        </text>
        <text x="30" y="16">
          ${high.toFixed(2)}
        </text>
        <text x="30" y="184">
          ${low.toFixed(2)}
        </text>
      </svg>
      <figcaption className="muted">
        {bars.at(-1)?.source} · {bars.at(-1)?.feed} · collected{" "}
        {formatAsOf(bars.at(-1)?.available_at ?? "")}. Daily history, not a live
        entry quote.
      </figcaption>
    </figure>
  );
}
