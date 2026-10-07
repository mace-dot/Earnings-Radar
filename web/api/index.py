"""Public research plus authenticated private watchlists and leased collection."""
import hmac
import json
import os
import re
import sys
from http.cookies import SimpleCookie
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).parent))
from _store import Store,StoreError
from _auth import current_user,auth_request,AuthError,cookie
from _collector import run,resolve_symbol,CollectionError
from _directory import search as directory_search
from _orchestrator import company,request_research,background
from _assistant import answer as company_answer
from _live import live_quote,capabilities,provider_get,enabled as market_enabled
from _options_research import research as option_research
from _policy import POLICY

class handler(BaseHTTPRequestHandler):
    def respond(self,status,payload,cookies=()):
        body=json.dumps(payload,allow_nan=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        for c in cookies:self.send_header('Set-Cookie',c)
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path='/api/'+parse_qs(urlsplit(self.path).query)['route'][0] if 'route' in parse_qs(urlsplit(self.path).query) else urlsplit(self.path).path
        try:
            store=Store()
            params=parse_qs(urlsplit(self.path).query)
            if path=='/api/directory':return self.respond(200,{'companies':directory_search(store,params.get('q',[''])[0])})
            if path=='/api/company':return self.respond(200,company(store,params.get('symbol',[''])[0].upper()))
            if path=='/api/capabilities':return self.respond(200,{**capabilities(store),'policy':POLICY})
            if path=='/api/quote':return self.respond(200,live_quote(store,params.get('symbol',[''])[0].upper()))
            if path=='/api/options':return self.respond(200,option_research(store,params.get('symbol',[''])[0].upper()))
            if path=='/api/diagnostics':
                secret=os.getenv('CRON_SECRET','')
                if not secret or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+secret):return self.respond(401,{'error':'Administrator authorization required'})
                status=capabilities(store)
                try:
                    bars=provider_get('/v2/stocks/AAPL/bars',{'timeframe':'1Day','limit':2,'feed':'iex'})
                    status['price_probe']={'authenticated':True,'received_bar_count':len(bars.get('bars',[]))}
                except Exception:status['price_probe']={'authenticated':False,'reason':'Provider probe failed'}
                return self.respond(200,status)
            if path=='/api/track-record':
                rows=store.request('radar_research_snapshots',query='select=*&order=created_at.desc&limit=50')
                evaluations=store.request('radar_evaluations',query='select=*&order=created_at.desc&limit=50') if market_enabled() else []
                if not market_enabled():
                    rows=[{**r,'payload':{k:r['payload'][k] for k in ('as_of','action','state','source_ids') if k in r['payload']}} for r in rows]
                return self.respond(200,{'snapshots':rows,'evaluations':evaluations,'forecast_status':'No validated predictive model has issued forecasts; outcomes require market prices.'})
            if path in ('/api/dashboard','/api/index','/api/index.py'):return self.respond(200,store.dashboard())
            if path=='/api/session':
                try:user=current_user(store,self.headers.get('Cookie'));return self.respond(200,{'user':{'id':user['id'],'email':user.get('email')}})
                except AuthError:return self.respond(200,{'user':None})
            if path=='/api/watchlist':
                user=current_user(store,self.headers.get('Cookie'))
                rows=store.request('radar_watchlists',query='select=symbol,created_at&user_id=eq.'+user['id']+'&order=created_at.asc')
                return self.respond(200,{'watchlist':[r['symbol'] for r in rows]})
            if path=='/api/ideas':
                user=current_user(store,self.headers.get('Cookie'))
                rows=store.request('radar_ideas',query='select=symbol,direction,evidence_id,created_at&user_id=eq.'+user['id']+'&order=created_at.desc&limit=50')
                return self.respond(200,{'ideas':rows})
            if path=='/api/collect':
                secret=os.getenv('CRON_SECRET','')
                if not secret or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+secret):return self.respond(401,{'error':'Scheduled collector authorization required'})
                return self.respond(200,background(store))
            return self.respond(404,{'error':'Unknown endpoint'})
        except AuthError as exc:self.respond(401,{'error':str(exc)})
        except ValueError as exc:self.respond(400,{'error':str(exc)})
        except StoreError as exc:self.respond(503,{'error':str(exc),'events':[],'status':[]})
        except Exception:self.respond(503,{'error':'Service temporarily unavailable; check deployment logs'})
    def do_POST(self):
        # Browser writes must originate on this website; cookies never authorize cross-site writes.
        origin=self.headers.get('Origin','');host=self.headers.get('Host','')
        if origin!='https://'+host:return self.respond(403,{'error':'Same-origin request required'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=16000:return self.respond(400,{'error':'Invalid request size'})
            payload=json.loads(self.rfile.read(size));path='/api/'+parse_qs(urlsplit(self.path).query)['route'][0] if 'route' in parse_qs(urlsplit(self.path).query) else urlsplit(self.path).path;store=Store()
            if not isinstance(payload,dict):return self.respond(400,{'error':'JSON object required'})
            if path=='/api/research':return self.respond(200,request_research(store,str(payload.get('symbol','')).upper()))
            if path=='/api/strategy':
                direction=payload.get('direction')
                if direction not in ('up','down'):return self.respond(400,{'error':'Choose up or down'})
                request_research(store,str(payload.get('symbol','')).upper())
                result=company(store,str(payload.get('symbol','')).upper())
                return self.respond(200,result['strategies'][direction])
            if path=='/api/assistant':return self.respond(200,company_answer(store,str(payload.get('symbol','')).upper(),payload.get('question','')))
            if path=='/api/session':
                action=payload.get('action')
                if action=='logout':return self.respond(200,{'user':None},[cookie('radar_session','',0),cookie('radar_refresh','',0)])
                if action=='refresh':
                    c=SimpleCookie();c.load(self.headers.get('Cookie',''));refresh=c.get('radar_refresh')
                    if not refresh:raise AuthError('Sign in again')
                    data=auth_request(store,'token?grant_type=refresh_token',{'refresh_token':refresh.value})
                else:
                    if action not in ('login','signup'):return self.respond(400,{'error':'Unknown sign-in action'})
                    email=payload.get('email','');password=payload.get('password','')
                    if not isinstance(email,str) or not isinstance(password,str) or len(email)>254 or not 8<=len(password)<=200:return self.respond(400,{'error':'Use an email and a password of at least 8 characters'})
                    data=auth_request(store,'signup' if action=='signup' else 'token?grant_type=password',{'email':email,'password':password})
                if not data.get('access_token'):return self.respond(200,{'confirmation_required':True})
                return self.respond(200,{'signed_in':True},[cookie('radar_session',data['access_token'],int(data.get('expires_in',3600))),cookie('radar_refresh',data['refresh_token'],604800)])
            user=current_user(store,self.headers.get('Cookie'))
            if path=='/api/collect':return self.respond(200,run(store))
            if path=='/api/ideas':
                symbol=payload.get('symbol');direction=payload.get('direction')
                if not isinstance(symbol,str) or not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}',symbol) or direction not in ('up','down'):return self.respond(400,{'error':'Choose a company and an up or down research idea'})
                if payload.get('action')=='remove':
                    store.request('radar_ideas',query='user_id=eq.'+user['id']+'&symbol=eq.'+symbol+'&direction=eq.'+direction,method='DELETE')
                elif payload.get('action')=='save':
                    eid=payload.get('evidence_id')
                    if not isinstance(eid,str) or not re.fullmatch(r'[a-f0-9]{64}',eid):return self.respond(400,{'error':'Supporting evidence required'})
                    evidence=store.request('radar_events',query='select=tickers&id=eq.'+eid+'&limit=1')
                    if not evidence or symbol not in evidence[0]['tickers']:return self.respond(400,{'error':'Evidence does not support this company'})
                    existing=store.request('radar_ideas',query='select=symbol,direction&user_id=eq.'+user['id']+'&limit=50')
                    if len(existing)>=20 and not any(r['symbol']==symbol and r['direction']==direction for r in existing):return self.respond(400,{'error':'Keep up to 20 saved research ideas'})
                    store.request('radar_ideas',rows=[{'user_id':user['id'],'symbol':symbol,'direction':direction,'evidence_id':eid}],conflict='user_id,symbol,direction')
                else:return self.respond(400,{'error':'Unknown idea action'})
                return self.respond(200,{'saved':True})
            if path=='/api/watchlist':
                symbol=payload.get('symbol','').strip().upper()
                if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}',symbol):return self.respond(400,{'error':'Invalid ticker'})
                if payload.get('action')=='remove':store.request('radar_watchlists',query='user_id=eq.'+user['id']+'&symbol=eq.'+symbol,method='DELETE')
                elif payload.get('action')=='add':
                    resolve_symbol(store,symbol)
                    store.request('radar_watchlists',rows=[{'user_id':user['id'],'symbol':symbol}],conflict='user_id,symbol',ignore=True)
                else:return self.respond(400,{'error':'Unknown watchlist action'})
                return self.respond(200,{'saved':True,'symbol':symbol})
            return self.respond(404,{'error':'Unknown endpoint'})
        except (ValueError,TypeError):self.respond(400,{'error':'Invalid request'})
        except AuthError as exc:self.respond(401,{'error':str(exc)})
        except CollectionError as exc:self.respond(400,{'error':str(exc)})
        except StoreError as exc:self.respond(503,{'error':str(exc)})
        except Exception:self.respond(503,{'error':'Service temporarily unavailable'})
