export default function Methodology() {
  return (
    <>
      <p className="eyebrow">HOW RADAR WORKS</p>
      <h1>Evidence before confidence.</h1>
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
