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

    def request(self, table, *, query='', rows=None, conflict='id', ignore=False, method=None):
        if table not in {'radar_events', 'radar_status', 'radar_watchlists', 'radar_collection_state', 'radar_ideas'}:
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
            method=method or ('POST' if rows is not None else 'GET'))
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
        try:
            from ._research import enrich, financial_context
        except ImportError:
            from _research import enrich, financial_context
        events = enrich(self.request('radar_events', query='select=*&order=published_at.desc&limit=600'))
        status = self.request('radar_status', query='select=*&id=eq.collector&limit=1')
        symbols=sorted({s for e in events for s in e.get('tickers',[])})
        contexts={s:financial_context(events,s) for s in symbols}
        try:
            from ._board import company_board
        except ImportError:
            from _board import company_board
        return {'events':events,'status':status,'financial_context':contexts,
                'move_board':company_board(events,contexts,status[0]['payload'] if status else {}),
                'weekly': [e['id'] for e in events if e['research']['ranking']['eligible_weekly']][:5],
                'source_health': self.source_health(events,status)}

    def rpc(self, name, payload):
        if name != 'radar_claim_collection': raise ValueError('Unknown RPC')
        headers={'apikey':self.key,'Content-Type':'application/json'}
        if not self.key.startswith('sb_secret_'):headers['Authorization']='Bearer '+self.key
        try:
            with urlopen(Request(self.url+'/rest/v1/rpc/'+name, data=json.dumps(payload).encode(),headers=headers),timeout=20) as r:
                return json.load(r)
        except (HTTPError,URLError):raise StoreError('Collection lease unavailable') from None

    def finish_collection(self,owner,error):
        from datetime import datetime,timezone
        self.request('radar_collection_state',query='id=eq.true&owner=eq.'+owner,
                     rows=None,method='GET')
        headers={'apikey':self.key,'Content-Type':'application/json'}
        if not self.key.startswith('sb_secret_'):headers['Authorization']='Bearer '+self.key
        payload={'lease_until':None,'last_finished':datetime.now(timezone.utc).isoformat(),'last_error':error}
        with urlopen(Request(self.url+'/rest/v1/radar_collection_state?id=eq.true&owner=eq.'+owner,
                     data=json.dumps(payload).encode(),headers=headers,method='PATCH'),timeout=20) as r:r.read()

    def source_health(self,events,status):
        state=status[0]['payload'] if status else {};jobs=state.get('jobs',[])
        registry=state.get('sources',[])
        by_id={s['id']:dict(s) for s in registry}
        for sid,name in [('sec','SEC filings'),('sec_fundamentals','SEC financial facts'),('fed_press','Federal Reserve releases'),('fed_speeches','Federal Reserve speeches')]:
            by_id.setdefault(sid,{'id':sid,'name':name,'documentation_url':'https://www.sec.gov' if sid.startswith('sec') else 'https://www.federalreserve.gov','capabilities':'Official source evidence'})
        for sid,s in by_id.items():
            matching=[e for e in events if e['provider']==sid or sid=='sec' and e['provider']=='sec_document']
            related=[j for j in jobs if j['name']==sid or j['name'].startswith(sid+':') or sid=='sec_fundamentals' and j['name'].startswith('sec:')]
            last=max((j['last_success'] for j in related if j.get('last_success')),default=None)
            if matching and last:s['integration_status']='working integration'
            elif s.get('access_status')=='licensed_access_required':s['integration_status']='licensed access required'
            elif sid in ('sec','sec_fundamentals','fed_press','fed_speeches','alpaca_news','alpaca_market'):s['integration_status']='available but not configured'
            else:s['integration_status']='unsupported'
            s.update({'last_success':last,'records':len(matching),'errors':[j['last_error'] for j in related if j.get('last_error')],
                      'last_retrieval':max((e['retrieved_at'] for e in matching),default=None)})
        return list(by_id.values())
