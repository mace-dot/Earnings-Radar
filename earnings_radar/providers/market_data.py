"""Concrete IEX stock quote adapter. It does not establish options entitlement."""
from earnings_radar.providers.base import HTTP
from earnings_radar.providers.news import alpaca_headers
from earnings_radar.validation import number, utc_timestamp, ticker

class AlpacaMarketData:
    def __init__(self,http=None): self.http=http or HTTP()
    def collect(self,tickers):
        data=self.http.get_json('https://data.alpaca.markets/v2/stocks/quotes/latest',headers=alpaca_headers(),params={'symbols':','.join(tickers),'feed':'iex'})
        rows=[]
        for symbol,q in data.get('quotes',{}).items():
            bid,ask=number(q['bp']),number(q['ap'])
            if bid is None or ask is None or bid>ask: raise ValueError('invalid stock quote')
            rows.append({'ticker':ticker(symbol),'bid':bid,'ask':ask,'timestamp':utc_timestamp(q['t']),'feed_type':'indicative','provider':'alpaca_iex','bid_size':number(q.get('bs'),integer=True),'ask_size':number(q.get('as'),integer=True)})
        return rows
