"""Small server-only Supabase REST client; credentials never reach the browser."""
import json
import os
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class StoreError(RuntimeError):
    pass

class Store:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL', '').rstrip('/')
        self.key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
        if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', self.url) or not self.key:
            raise StoreError('Database connection is not configured')

    def request(self, table, *, query='', rows=None, conflict='id', ignore=False):
        if table not in {'radar_events', 'radar_status'}:
            raise ValueError('Unknown table')
        if rows is not None:
            query = 'on_conflict=' + conflict
        req = Request(self.url + '/rest/v1/' + table + '?' + query,
            data=json.dumps(rows).encode() if rows is not None else None,
            headers={'apikey': self.key, 'Authorization': 'Bearer ' + self.key,
                     'Content-Type': 'application/json',
                     'Prefer': ('resolution=ignore-duplicates' if ignore else 'resolution=merge-duplicates') + ',return=minimal'},
            method='POST' if rows is not None else 'GET')
        try:
            with urlopen(req, timeout=20) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise StoreError('Database response exceeds limit')
                return json.loads(body) if body else None
        except (HTTPError, URLError):
            raise StoreError('Database request failed; check project configuration') from None

    def dashboard(self):
        return {'events': self.request('radar_events', query='select=*&order=published_at.desc&limit=150'),
                'status': self.request('radar_status', query='select=*&id=eq.collector&limit=1')}
