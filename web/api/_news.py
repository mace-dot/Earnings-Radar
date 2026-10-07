"""Public RSS headlines with publisher links; no paywall or article-body scraping."""
import time
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit,quote
from urllib.request import Request,build_opener,HTTPRedirectHandler
from xml.etree import ElementTree
try:
 from ._collector import event,CollectionError,Text
except ImportError:
 from _collector import event,CollectionError,Text

FEEDS=[('cnbc_rss','CNBC','https://www.cnbc.com/id/100003114/device/rss/rss.html',{'www.cnbc.com','www.nbcnews.com'},'secondary'),
 ('bls_rss','Bureau of Labor Statistics','https://www.bls.gov/feed/bls_latest.rss',{'www.bls.gov'},'primary'),
 ('bea_rss','Bureau of Economic Analysis','https://www.bea.gov/rss/rss.xml',{'www.bea.gov','apps.bea.gov'},'primary')]
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args):return None

def get_feed(url):
 if urlsplit(url).hostname not in {'www.cnbc.com','www.bls.gov','www.bea.gov','feeds.finance.yahoo.com'}:raise CollectionError('Unexpected news destination')
 try:
  with build_opener(NoRedirect()).open(Request(url,headers={'User-Agent':'EarningsRadar RSS reader mace@udel.edu'}),timeout=8) as r:body=r.read(1000001)
  if len(body)>1000000:raise CollectionError('RSS response exceeded limit')
  return body
 except CollectionError:raise
 except Exception:raise CollectionError('Public RSS unavailable; no restricted fallback attempted') from None

def parse_feed(body,provider,publisher,hosts,provenance,symbol=None,now=None):
 now=now or datetime.now(timezone.utc)
 if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():raise CollectionError('Unsafe RSS declarations')
 root=ElementTree.fromstring(body);rows=[]
 for item in root.findall('./channel/item')[:20]:
  url=item.findtext('link','').strip();u=urlsplit(url)
  if u.scheme!='https' or u.hostname not in hosts or u.username or u.password:continue
  try:pub=parsedate_to_datetime(item.findtext('pubDate',''))
  except (ValueError,TypeError):continue
  if pub.tzinfo is None or pub>now:continue
  parser=Text();parser.feed(item.findtext('title',''));title=' '.join(''.join(parser.parts).split())[:400]
  if not title:continue
  row=event(provider,item.findtext('guid') or url,title,url,pub.isoformat(),[symbol] if symbol else [],
    {'source_kind':'publisher RSS headline','full_article_collected':False,'relevance':'provider ticker feed association; not causal evidence' if symbol else 'macro context'},publisher,'reporting' if provenance=='secondary' else 'primary_evidence',provenance=provenance)
  row['analysis']['category']='general' if symbol else 'systemic';row['backfill']=False
  rows.append(row)
 return rows

def collect_news(store,symbol=None,deadline=None):
 configs=[('yahoo_rss','Yahoo Finance','https://feeds.finance.yahoo.com/rss/2.0/headline?s='+quote(symbol)+'&region=US&lang=en-US',{'finance.yahoo.com','www.yahoo.com','feeds.finance.yahoo.com'},'secondary')] if symbol else FEEDS
 jobs=[]
 for provider,publisher,url,hosts,provenance in configs:
  if deadline and time.monotonic()>deadline-8:break
  try:
   rows=parse_feed(get_feed(url),provider,publisher,hosts,provenance,symbol)
   if not rows:raise CollectionError('No supported timestamped RSS headlines')
   for i in range(0,len(rows),20):store.request('radar_events',rows=rows[i:i+20])
   jobs.append({'name':provider+(':'+symbol if symbol else ''),'status':'complete','records':len(rows),'last_success':datetime.now(timezone.utc).isoformat(),'last_error':None})
  except Exception as exc:jobs.append({'name':provider+(':'+symbol if symbol else ''),'status':'unavailable','records':0,'last_error':str(exc) if isinstance(exc,CollectionError) else 'RSS parse failed'})
 return jobs

def refresh_company(store,symbol):
 if not store.rpc('radar_claim_news',{'p_symbol':symbol}):return []
 jobs=collect_news(store,symbol,deadline=time.monotonic()+12)
 store.request('radar_market_cache',query='symbol=eq.'+symbol,rows={'news_status':jobs},method='PATCH')
 return jobs
