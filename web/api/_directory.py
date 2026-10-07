"""Official identifier cache and independent filing discovery, not market-price data."""
from datetime import datetime,timezone,timedelta
import re
import time
try:
 from ._collector import Fetch,CollectionError
except ImportError:
 from _collector import Fetch,CollectionError

DIRECTORY='https://www.sec.gov/files/company_tickers_exchange.json'

def all_companies(store):
 rows=[]
 for offset in range(0,20000,1000):
  page=store.request('radar_universe',query=f'select=*&order=symbol.asc&limit=1000&offset={offset}')
  rows.extend(page)
  if len(page)<1000:return rows
 raise CollectionError('Directory exceeded bounded cache capacity')

def refresh_directory(store,fetch=None):
 fetch=fetch or Fetch(time.monotonic()+30);data=fetch.json(DIRECTORY)
 if not {'cik','name','ticker','exchange'}.issubset(data.get('fields',[])):raise CollectionError('Unexpected SEC directory format')
 old={r['symbol']:r for r in all_companies(store)};rows=[];seen=set();now=datetime.now(timezone.utc).isoformat()
 for values in data['data']:
  c=dict(zip(data['fields'],values));symbol=str(c['ticker']).upper()
  if not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,14}',symbol):continue
  cik=str(c['cik']).zfill(10)
  if not re.fullmatch(r'\d{10}',cik):continue
  existing=old.get(symbol,{});aliases=existing.get('aliases',[])
  if existing.get('name') and existing['name']!=c['name']:aliases=list(dict.fromkeys(aliases+[existing['name']]))[-20:]
  rows.append({'symbol':symbol,'cik':cik,'name':c['name'],'exchange':c['exchange'],'active':True,'aliases':aliases,'retrieved_at':now,'source_url':DIRECTORY});seen.add(symbol)
 if len(rows)<1000:raise CollectionError('Unexpectedly small directory; cached identifiers preserved')
 for symbol,r in old.items():
  if symbol not in seen:rows.append({**r,'active':False,'retrieved_at':now})
 for i in range(0,len(rows),400):store.request('radar_universe',rows=rows[i:i+400],conflict='symbol')
 return len(seen)

def search(store,query):
 if not isinstance(query,str) or not 1<=len(query.strip())<=60:return []
 return store.rpc('radar_search_directory',{'p_query':query.strip()})

def parse_index(body,day):
 text=body.decode('utf-8',errors='replace')
 if 'CIK|Company Name|Form Type|Date Filed|File Name' not in text:raise CollectionError('Unexpected SEC daily index format')
 output=[]
 for line in text.splitlines():
  fields=line.split('|')
  if len(fields)!=5:continue
  cik,name,form,filed,path=fields
  if form not in ('8-K','8-K/A','10-Q','10-K','20-F','6-K','40-F'):continue
  if not cik.isdigit() or not re.fullmatch(r'edgar/data/\d+/\d{10}-\d{2}-\d{6}\.txt',path):continue
  normalized=filed.replace('-','')
  if normalized!=day.strftime('%Y%m%d'):continue
  output.append({'cik':cik.zfill(10),'form':form,'filed':day.isoformat(),'url':'https://www.sec.gov/Archives/'+path})
 return output

def discover(store,fetch=None,now=None):
 now=now or datetime.now(timezone.utc);fetch=fetch or Fetch(time.monotonic()+35)
 companies=all_companies(store);by_cik={}
 for c in companies:
  if c['active']:by_cik.setdefault(c['cik'],[]).append(c)
 for ago in range(1,5):
  day=now.date()-timedelta(days=ago)
  if day.weekday()>=5:continue
  url=f'https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{(day.month-1)//3+1}/master.{day:%Y%m%d}.idx'
  try:filings=parse_index(fetch.get(url),day)
  except CollectionError as exc:
   if str(exc)=='Source HTTP 404':continue
   raise
  matches=[];seen=set()
  for filing in sorted(filings,key=lambda x:(0 if x['form'] in ('10-Q','10-K','20-F') else 1,x['cik'])):
   for company in sorted(by_cik.get(filing['cik'],[]),key=lambda c:(len(c['symbol']),c['symbol']))[:1]:
    if company['symbol'] in seen:continue
    seen.add(company['symbol']);matches.append({**company,'discovery_form':filing['form'],'discovery_date':filing['filed'],'discovery_source':filing['url']})
  accepted=0
  for c in matches[:12]:
   queued=store.rpc('radar_enqueue',{'p_symbol':c['symbol'],'p_reason':'filing','p_priority':60 if c['discovery_form'] in ('10-Q','10-K','20-F') else 40})
   if queued.get('status')!='daily_capacity':accepted+=1
  return {'index_url':url,'date':day.isoformat(),'matched_companies':len(matches),'queued':accepted,'candidates':matches[:30]}
 raise CollectionError('No recent daily filing index available')
