export default function Learn() {
  return (
    <>
      <p className="eyebrow">START HERE</p>
      <h1>A stock setup in plain English</h1>
      <div className="grid">
        {[
          [
            "BULL and BEAR",
            "BULL studies reasons a price could rise. BEAR studies reasons it could fall. On a volatility line, the buttons describe volatility rising or falling instead.",
          ],
          [
            "Buying a call or put",
            "A call can gain when a stock rises; a put can gain when it falls. Both can lose their entire purchase price, even if the direction is right but the move is too late or too small.",
          ],
          [
            "An earnings report",
            "A company reports its results. Prices often react to the difference between results and expectations, rather than simply to good or bad results.",
          ],
          [
            "Expected move",
            "Option prices can imply a range of movement. It is not a promised range or a real-world probability of profit.",
          ],
          [
            "Lean versus probability",
            "Lean is an unvalidated research assessment. A percentage requires enough untouched historical cases and a calibration report for the same setup.",
          ],
          [
            "Stops and gaps",
            "A stop is a plan to exit, not a guaranteed selling price. Overnight news can make shares jump past the stop. Shareholders can lose their entire investment.",
          ],
        ].map(([title, text]) => (
          <article className="card" key={title}>
            <h2>{title}</h2>
            <p>{text}</p>
          </article>
        ))}
      </div>
    </>
  );
}
