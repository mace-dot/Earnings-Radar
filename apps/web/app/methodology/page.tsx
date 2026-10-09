export default function Methodology() {
  return (
    <>
      <p className="eyebrow">HOW RADAR WORKS</p>
      <h1>Evidence before confidence.</h1>
      <section className="panel">
        <h2>How to read a ticker result</h2>
        <p>
          A company page answers three questions. How large a move could be.
          Which way the saved evidence leans. What a recent Stocktwits sample
          says. Reddit is not connected. A lean is not a forecast, and no chance
          of profit is published until testing earns it.
        </p>
      </section>
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
      <section className="panel">
        <h2>What is running now</h2>
        <p>
          The engine collects SEC identifiers and sourced daily closing prices,
          stores source and collection times, and calculates price changes and
          volatility. Both sides of each setup expose missing inputs. Current
          explanations are rule templates, not independent deep research or a
          trained prediction model.
        </p>
        <h2>What still needs validation</h2>
        <p>
          Historical earnings cases, revisions and executable options quotes are
          needed before validated probabilities or executable trade candidates
          can be published. Unvalidated paper contract comparisons are kept
          separate. Prospective stock-move testing freezes inputs and evaluates
          five later exchange sessions. Training, calibration and test periods
          stay separate, with overlapping outcomes excluded. The model cannot
          approve itself.
        </p>
        <h2>Data limits</h2>
        <p>
          Nasdaq history has an unspecified corporate-action adjustment basis. A
          Massive account can supply split-adjusted daily aggregates when its
          entitlement allows; split checks are required for model evaluation.
          Cboe options are delayed snapshots, not executable quotes. Finnhub
          prices retain their original timestamp. Older IEX observations remain
          labeled with their original source. Indicative options cannot
          establish an executable price. Provider agreement does not confirm an
          earnings date; a company announcement is needed.
        </p>
        <h2>Track record rules</h2>
        <p>
          Published picks are immutable. All outcomes must be graded, with
          losers included. Stock direction and option profit are separate
          measurements. A stock-only backtest cannot validate a contract
          strategy.
        </p>
        <h2>No automatic brokerage orders</h2>
        <p>
          The app is paper research. It does not connect to Robinhood or place
          trades. Your account size is unknown until you choose to provide a
          budget.
        </p>
      </section>
    </>
  );
}
