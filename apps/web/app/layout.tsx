import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = {
  title: "Earnings Radar",
  description:
    "Understand earnings setups, price history and risk in plain English.",
};
export default function Layout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="skip">
          Skip to content
        </a>
        <header>
          <Link className="brand" href="/">
            ◉ EARNINGS <span>RADAR</span>
          </Link>
          <nav aria-label="Main navigation">
            <Link href="/">Board</Link>
            <Link href="/moves">Move screen</Link>
            <Link href="/picks">Picks</Link>
            <Link href="/track-record">Track record</Link>
            <Link href="/learn">Learn</Link>
            <Link href="/methodology">How it works</Link>
          </nav>
          <span className="pill">PAPER RESEARCH</span>
        </header>
        <main id="main">{children}</main>
        <footer>
          Evidence, timing, risk. Conditional setups — outcomes can differ. No
          brokerage orders are placed.
        </footer>
      </body>
    </html>
  );
}
