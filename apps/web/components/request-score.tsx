"use client";
import { useEffect, useState } from "react";
export function RequestScore({ symbol }: { symbol: string }) {
  const [state, setState] = useState("Requesting automated research…");
  useEffect(() => {
    let active = true;
    fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    })
      .then(async (r) => {
        if (!r.ok) throw new Error();
        const data = await r.json();
        if (active)
          setState(
            data.state === "completed"
              ? "Research collected. Refresh to see the latest snapshot."
              : data.state === "capacity"
                ? "Collector queue is at capacity. Try again later."
                : data.state === "failed"
                  ? "The last collection failed. Provider access needs review."
                  : "Research requested. Collection runs when the background worker is available.",
          );
      })
      .catch(() => {
        if (active)
          setState("Unable to request research right now. Try again later.");
      });
    return () => {
      active = false;
    };
  }, [symbol]);
  return (
    <div className="notice" role="status">
      {state}
    </div>
  );
}
