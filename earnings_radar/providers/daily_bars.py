"""Authorized Alpaca historical IEX bars; adjusted daily research, not real-time."""
from datetime import datetime, timezone, timedelta
from earnings_radar.providers.base import HTTP, ProviderError
from earnings_radar.providers.news import alpaca_headers

class DailyBars:
    def __init__(self, http=None): self.http = http or HTTP()

    def collect(self, symbols, now=None):
        now = now or datetime.now(timezone.utc)
        # Exclude the current UTC day to avoid using an incomplete daily bar.
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        params = {'symbols': ','.join(symbols), 'timeframe': '1Day', 'start': (end-timedelta(days=500)).isoformat(),
                  'end': (end-timedelta(seconds=1)).isoformat(), 'adjustment': 'all', 'feed': 'iex', 'limit': 10000}
        result = {s: [] for s in symbols}
        for _ in range(5):
            data = self.http.get_json('https://data.alpaca.markets/v2/stocks/bars', headers=alpaca_headers(), params=params)
            for s, rows in data.get('bars', {}).items():
                if s in result: result[s].extend(rows)
            token = data.get('next_page_token')
            if not token: return result
            params['page_token'] = token
        raise ProviderError('Historical bars exceeded bounded pagination')
