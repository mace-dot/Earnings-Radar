"""Authorized daily history; no unofficial quote scraping or synthetic prices."""
import json,os,math,re
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from urllib.parse import urlencode
try:
 from ._price_statistics import summarize
except ImportError:
 from _price_statistics import summarize

class MarketError(RuntimeError):pass
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args):return None

def validate_bars(rows,now=None):
 now=now or datetime.now(timezone.utc);out=[];seen=set();eastern=ZoneInfo('America/New_York')
 for b in rows:
  t=datetime.fromisoformat(b['t'].replace('Z','+00:00'))
  if t.tzinfo is None:raise ValueError('Market timestamps require timezone')
  session=t.astimezone(eastern).date();today=now.astimezone(eastern)
  if session>today.date() or session==today.date() and today.hour<16:continue
  if session.weekday()>4:raise ValueError('Unexpected weekend stock session')
  vals={k:float(b[k]) for k in ('o','h','l','c','v')}
  if any(not math.isfinite(v) for v in vals.values()) or min(vals[k] for k in ('o','h','l','c'))<=0 or vals['v']<0:raise ValueError('Invalid bar values')
  if not vals['l']<=min(vals['o'],vals['c'])<=max(vals['o'],vals['c'])<=vals['h']:raise ValueError('Invalid OHLC ordering')
  if session in seen:raise ValueError('Duplicate market session')
  seen.add(session);out.append({**vals,'t':t.astimezone(timezone.utc).isoformat(),'session':session.isoformat()})
 return sorted(out,key=lambda b:b['session'])

def collect_alpaca(symbol):
 if not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,14}',symbol):raise ValueError('Invalid ticker')
 key=os.getenv('ALPACA_API_KEY');secret=os.getenv('ALPACA_API_SECRET')
 if not key or not secret:raise MarketError('Alpaca free-account credentials are not configured')
 if os.getenv('RADAR_MARKET_DISPLAY_AUTHORIZED','false').lower()!='true':raise MarketError('Public price-display entitlement has not been confirmed; set RADAR_MARKET_DISPLAY_AUTHORIZED only after checking provider terms')
 params={'timeframe':'1Day','start':(datetime.now(timezone.utc)-timedelta(days=560)).date().isoformat()+'T00:00:00Z','limit':1000,'adjustment':'all','feed':'iex','sort':'asc'}
 url='https://data.alpaca.markets/v2/stocks/'+symbol+'/bars?'+urlencode(params)
 try:
  with build_opener(NoRedirect()).open(Request(url,headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret}),timeout=15) as r:
   body=r.read(1500001)
  if len(body)>1500000:raise MarketError('Price response exceeded bound')
  data=json.loads(body)
  if data.get('next_page_token'):raise MarketError('Incomplete history response; cached history preserved')
  bars=validate_bars(data.get('bars',[]))
  if len(bars)<2:raise MarketError('Provider returned insufficient price history')
  return {'provider':'Alpaca','feed':'IEX','adjustment':'all (provider split/dividend adjustments)','currency':'USD',
    'volume_scope':'IEX venue only; not consolidated market volume','cadence':'completed daily sessions; not live quotes',
    'retrieved_at':datetime.now(timezone.utc).isoformat(),'bars':bars,'statistics':summarize(bars),
    'source_url':'https://docs.alpaca.markets/docs/about-market-data-api'}
 except MarketError:raise
 except Exception:raise MarketError('Authorized price request failed; check credentials, entitlement and provider availability') from None

def history(store,symbol):
 rows=store.request('radar_market_cache',query='select=*&symbol=eq.'+symbol+'&limit=1')
 row=rows[0] if rows else {};payload=row.get('payload',{})
 if not payload.get('bars'):return {'status':'not_configured' if not os.getenv('ALPACA_API_KEY') or not os.getenv('ALPACA_API_SECRET') else 'unavailable','bars':[],
   'reason':row.get('last_error') or 'Connect ALPACA_API_KEY and ALPACA_API_SECRET in Vercel server environment settings for authorized daily stock history.',
   'news_status':row.get('news_status',[]),'statistics':{'status':'unavailable'},'required_credentials':['ALPACA_API_KEY','ALPACA_API_SECRET']}
 asof=datetime.fromisoformat(payload['bars'][-1]['session']).replace(tzinfo=timezone.utc)
 retrieved=datetime.fromisoformat(payload['retrieved_at'].replace('Z','+00:00'))
 stale=(datetime.now(timezone.utc)-asof).days>5 or (datetime.now(timezone.utc)-retrieved).total_seconds()>36*3600
 return {**payload,'status':'stale' if stale else 'available','last_error':row.get('last_error'),'news_status':row.get('news_status',[])}

def refresh(store,symbol):
 if not os.getenv('ALPACA_API_KEY') or not os.getenv('ALPACA_API_SECRET'):return history(store,symbol)
 if not store.rpc('radar_claim_market',{'p_symbol':symbol}):return history(store,symbol)
 try:
  payload=collect_alpaca(symbol)
  store.request('radar_market_cache',query='symbol=eq.'+symbol,rows={'payload':payload,'updated_at':payload['retrieved_at'],'last_error':None,'lease_until':None},method='PATCH')
 except MarketError as exc:
  store.request('radar_market_cache',query='symbol=eq.'+symbol,rows={'last_error':str(exc),'lease_until':None},method='PATCH')
 return history(store,symbol)
