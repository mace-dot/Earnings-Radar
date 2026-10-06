"""Curated source registry. Reputation does not replace provenance or access rights."""
import os
from pathlib import Path
from earnings_radar.config import DATA_DIR
from earnings_radar.db import init_db

SOURCES = [
('sec','SEC','primary','https://www.sec.gov/search-filings/edgar-application-programming-interfaces','configured_contact_required','SEC submissions metadata; not future earnings dates'),
('sec_fundamentals','SEC XBRL fundamentals','primary','https://www.sec.gov/search-filings/edgar-application-programming-interfaces','configured_contact_required','Historical reported revenue, net income and gross profit; no consensus or upcoming earnings forecast'),
('fed_press','Federal Reserve','primary','https://www.federalreserve.gov/feeds/feeds.htm','public','Official press releases and policy documents'),
('fed_speeches','Federal Reserve speeches','institutional_research','https://www.federalreserve.gov/feeds/feeds.htm','public','Attributed opinion; not automatically enacted policy'),
('alpaca_news','Alpaca news','news','https://docs.alpaca.markets/reference/news-3','credentials_required','Entitled news metadata; source attribution retained'),
('alpaca_market','Alpaca IEX','market_data','https://docs.alpaca.markets/docs/market-data-faq','credentials_required','Single-exchange indicative quotes; no options coverage'),
('bloomberg','Bloomberg','news','https://www.bloomberg.com/professional/','licensed_access_required','Needs licensed API/data-feed agreement; no paywall scraping'),
('wsj','Wall Street Journal / Dow Jones','news','https://www.wsj.com/','licensed_access_required','Needs authorized Dow Jones feed/API and retention agreement'),
('earningshub','EarningsHub','earnings_calendar','https://earningshub.com/','authorized_api_unconfirmed','Website identified; authorized API and retention terms still unverified'),
('seeking_alpha','Seeking Alpha','institutional_research','https://seekingalpha.com/','licensed_access_required','Contributor opinion distinguished from primary evidence; licensed feed required'),
('yahoo_finance','Yahoo Finance','news_market_data','https://finance.yahoo.com/','authorized_api_unconfirmed','No unofficial endpoint or cookie/auth workaround'),
('google_finance','Google Finance','market_data','https://www.google.com/finance/','authorized_api_unconfirmed','No supported authorized API verified; do not scrape'),
('truth_social','Truth Social','political_statement','https://truthsocial.com/','authorized_api_unconfirmed','Direct access/pricing not verified; original statements differ from enacted policy'),
]

def research_path():
    return Path(os.getenv('RADAR_RESEARCH_DB_PATH', str(DATA_DIR / 'research.db')))

def prepare(path=None):
    path=init_db(path or research_path())
    from earnings_radar.db import get_conn
    with get_conn(path) as conn:
        for source in SOURCES:
            conn.execute('INSERT INTO source_registry(id,name,category,documentation_url,access_status,capabilities) VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET documentation_url=excluded.documentation_url,access_status=excluded.access_status,capabilities=excluded.capabilities',source)
    return path
