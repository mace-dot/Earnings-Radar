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
        self.key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '') or os.getenv('SUPABASE_SECRET_KEY', '')
        if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', self.url) or not self.key:
            raise StoreError('Database connection is not configured')

    def request(self, table, *, query='', rows=None, conflict='id', ignore=False):
        if table not in {'radar_events', 'radar_status'}:
            raise ValueError('Unknown table')
        if rows is not None:
            query = 'on_conflict=' + conflict
        headers = {'apikey': self.key, 'Content-Type': 'application/json',
                   'Prefer': ('resolution=ignore-duplicates' if ignore else 'resolution=merge-duplicates') + ',return=minimal'}
        if not self.key.startswith('sb_secret_'):
            headers['Authorization'] = 'Bearer ' + self.key
        req = Request(self.url + '/rest/v1/' + table + '?' + query,
            data=json.dumps(rows).encode() if rows is not None else None,
            headers=headers,
            method='POST' if rows is not None else 'GET')
        try:
            with urlopen(req, timeout=20) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise StoreError('Database response exceeds limit')
                return json.loads(body) if body else None
        except HTTPError as exc:
            messages = {401: 'Supabase rejected the server key. Check the project URL and server credential.',
                        403: 'Supabase access denied. Apply the research schema and server-role permissions.',
                        404: 'Research tables are missing. Run the Earnings Radar SQL migration in Supabase.'}
            raise StoreError(messages.get(exc.code, 'Database request failed; check project configuration')) from None
        except URLError:
            raise StoreError('Supabase is unreachable; check project URL and whether the project is paused') from None

    def dashboard(self):
        return {'events': self.request('radar_events', query='select=*&order=published_at.desc&limit=150'),
                'status': self.request('radar_status', query='select=*&id=eq.collector&limit=1')}
