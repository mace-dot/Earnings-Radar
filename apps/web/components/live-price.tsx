"use client";
import { useEffect, useState } from "react";
export function LivePrice({
  symbol,
  initialPrice,
  initialTime,
}: {
  symbol: string;
  initialPrice?: number;
  initialTime?: string;
}) {
  const [quote, setQuote] = useState({
    price: initialPrice,
    as_of: initialTime,
  });
  const [message, setMessage] = useState("Checking the latest observed trade…");
  useEffect(() => {
    let active = true;
    async function refresh() {
      if (document.hidden) return;
      try {
        const response = await fetch("/api/market", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol }),
        });
        const data = await response.json();
        if (active) {
          if (typeof data.price === "number") {
            setQuote({ price: data.price, as_of: data.as_of });
            setMessage("Updates while this page is open · partial IEX feed");
          } else {
            setMessage(
              "Refresh unavailable; showing the last stored observation.",
            );
          }
        }
      } catch {
        if (active)
          setMessage(
            "Refresh unavailable; showing the last stored observation.",
          );
      }
    }
    void refresh();
    const timer = setInterval(() => void refresh(), 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [symbol]);
  return (
    <section className="panel">
      <h2>Observed market price</h2>
      {quote.price !== undefined ? (
        <p className="metric">${quote.price.toFixed(2)}</p>
      ) : (
        <p>No price observed yet.</p>
      )}
      <p>{message}</p>
      {quote.as_of && (
        <small>
          Alpaca · trade time {new Date(quote.as_of).toLocaleString()}. Older
          trades remain labeled with their actual time; this is not a
          consolidated market quote.
        </small>
      )}
    </section>
  );
}
