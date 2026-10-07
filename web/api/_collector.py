"""Bounded official-source collector for the free daily Vercel schedule."""
import hashlib
import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree
from urllib.parse import urlsplit

CIKS={'AAPL':'0000320193','MSFT':'0000789019','NVDA':'0001045810','AMZN':'0001018724','TSLA':'0001318605','META':'0001326801','GOOGL':'0001652044','GOOG':'0001652044','JPM':'0000019617','WMT':'0000104169','XOM':'0000034088','NFLX':'0001065280','AMD':'0000002488','DIS':'0001744489','BAC':'0000070858'}
TAGS=['RevenueFromContractWithCustomerExcludingAssessedTax','NetIncomeLoss','GrossProfit','OperatingIncomeLoss','NetCashProvidedByUsedInOperatingActivities','PaymentsToAcquirePropertyPlantAndEquipment','Assets','Liabilities','InterestExpense']
FEEDS={'fed_press':'https://www.federalreserve.gov/feeds/press_all.xml','fed_speeches':'https://www.federalreserve.gov/feeds/speeches.xml'}
class CollectionError(RuntimeError):pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args):return None

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in ('script','style'):self.skip+=1
        if t in ('p','div','tr','br','li','h1','h2','h3') and not self.skip:self.parts.append('\n')
    def handle_endtag(self,t):
        if t in ('script','style'):self.skip=max(0,self.skip-1)
        if t in ('p','div','tr','li'):self.parts.append('\n')
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)

def excerpts(body):
    parser=Text();parser.feed(body.decode('utf-8',errors='replace'))
    paragraphs=[' '.join(p.split()) for p in ''.join(parser.parts).split('\n') if p.strip()]
    terms=('revenue','margin','cash flow','outlook','liquidity','net income','net loss','interest rate','inflation','monetary policy')
    output=[];offset=0
    for p in paragraphs:
        if len(p)>45 and any(t in p.lower() for t in terms):output.append({'text':p[:1200],'start':offset,'end':offset+min(len(p),1200)})
        offset+=len(p)+1
        if len(output)>=5:break
    return output

class Fetch:
    def __init__(self,deadline):self.deadline=deadline;self.last=0;self.opener=build_opener(NoRedirect())
    def get(self,url,limit=5_000_000):
        u=urlsplit(url)
        if u.scheme!='https' or u.hostname not in {'data.sec.gov','www.sec.gov','www.federalreserve.gov'} or u.username or u.password or u.port not in (None,443):raise CollectionError('Unexpected source destination')
        if time.monotonic()>self.deadline:raise CollectionError('Collection time budget reached')
        time.sleep(max(0,.3-(time.monotonic()-self.last)));self.last=time.monotonic()
        contact=os.getenv('SEC_USER_AGENT','EarningsRadar mace@udel.edu')
        if not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',contact):raise CollectionError('SEC contact identification missing')
        try:
            with self.opener.open(Request(url,headers={'User-Agent':contact}),timeout=12) as r:
                body=r.read(limit+1)
                if len(body)>limit:raise CollectionError('Source response exceeded limit')
                return body
        except HTTPError as e:raise CollectionError('Source HTTP '+str(e.code)) from None
        except (URLError,TimeoutError):raise CollectionError('Source connection failed') from None
    def json(self,url):return json.loads(self.get(url))

def event(provider,pid,title,url,published,tickers=(),metadata=None,institution='SEC',claim='primary_evidence'):
    metadata=metadata or {};now=datetime.now(timezone.utc).isoformat()
    payload={'title':title,'url':url,'published_at':published,'tickers':list(tickers),'metadata':metadata,'provenance':'primary','claim_type':claim}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    identity=hashlib.sha256(json.dumps([provider,pid,digest]).encode()).hexdigest()
    facts=[{'evidence_id':identity,'field':'title','excerpt':title}]
    facts += [{'evidence_id':identity,'field':'document_excerpt',**s} for s in metadata.get('excerpts',[])[:3]]
    category='earnings' if provider.startswith('sec') else 'systemic'
    analysis={'event_id':identity,'affected_tickers':list(tickers),'confirmed_facts':facts,'hypotheses':[],
              'economic_mechanism':'Primary disclosure requires comparison with financial history and documented expectations.',
              'bullish_implications':[],'bearish_implications':[],'counterevidence':[],'time_horizon':'Historical disclosure; future catalyst unconfirmed',
              'observed_reaction':'Not verified','suggested_action':'investigate','invalidation_conditions':['Source correction or conflicting primary evidence'],
              'missing_information':['Documented consensus expectations','Fresh market context'],'evidence_confidence':'medium','category':category,'policy_status':'not_applicable',
              'caveat':'Primary-source facts and conditional interpretation; no probability of trading success.'}
    return {'id':identity,'provider':provider,'provider_event_id':pid,'content_hash':digest,'title':title,'url':url,'institution':institution,
            'published_at':published,'retrieved_at':now,'tickers':list(tickers),'analysis':analysis,'evidence_meta':metadata,
            'provenance':'primary','claim_type':claim,'backfill':True,'story_key':hashlib.sha256(url.encode()).hexdigest()}

def collect_company(fetch,symbol,cik):
    rows=[];data=fetch.json(f'https://data.sec.gov/submissions/CIK{cik}.json');recent=data.get('filings',{}).get('recent',{})
    for i,pid in enumerate(recent.get('accessionNumber',[])[:25]):
        form=recent['form'][i]
        if form not in ('8-K','8-K/A','10-Q','10-Q/A','10-K','10-K/A'):continue
        doc=recent['primaryDocument'][i]
        if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',pid) or not re.fullmatch(r'[A-Za-z0-9_.-]+',doc):continue
        pub=datetime.fromisoformat(recent['acceptanceDateTime'][i].replace('Z','+00:00'))
        pub=pub.replace(tzinfo=timezone.utc) if pub.tzinfo is None else pub
        if pub>datetime.now(timezone.utc):continue
        url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{pid.replace("-","")}/{doc}'
        meta={'form':form,'cik':cik,'report_date':recent.get('reportDate',['']*len(recent['form']))[i]}
        if len(rows)<2:
            try:meta['excerpts']=excerpts(fetch.get(url,20_000_000))
            except CollectionError as exc:meta['document_error']=str(exc)
        rows.append(event('sec',pid,f'{symbol} filed {form}',url,pub.astimezone(timezone.utc).isoformat(),[symbol],meta))
        if len(rows)>=5:break
    for tag in TAGS:
        url=f'https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json'
        try:concept=fetch.json(url)
        except CollectionError as exc:
            if str(exc)=='Source HTTP 404':continue
            raise
        periods={}
        for f in concept.get('units',{}).get('USD',[]):
            if f.get('form') not in ('10-K','10-Q','10-K/A','10-Q/A') or not f.get('end'):continue
            if not isinstance(f.get('val'),(float,int)) or not math.isfinite(f['val']):continue
            end=datetime.fromisoformat(f['end']);start=datetime.fromisoformat(f['start']) if f.get('start') else None
            days=(end-start).days if start else None
            if days is not None and not (70<=days<=105 or 350<=days<=380):continue
            pub=datetime.fromisoformat(f['filed']).replace(hour=23,minute=59,second=59,tzinfo=timezone.utc)
            if pub>datetime.now(timezone.utc):continue
            key=(f.get('start'),f['end'])
            if key not in periods or (f['filed'],f['accn'])>(periods[key]['filed'],periods[key]['accn']):periods[key]=f
        for (start,end),f in sorted(periods.items(),key=lambda x:x[0][1],reverse=True)[:8]:
            pub=datetime.fromisoformat(f['filed']).replace(hour=23,minute=59,second=59,tzinfo=timezone.utc).isoformat()
            m={'tag':tag,'value':f['val'],'units':'USD','start':start,'end':end,'filed':f['filed'],'accession':f['accn'],'publication_precision':'filing_date_end_of_day_bound'}
            rows.append(event('sec_fundamentals',f'{symbol}:{tag}:{start}:{end}',f'{symbol}: {tag} {f["val"]:,.0f} USD for {start or "balance at"} to {end}',url,pub,[symbol],m,'SEC XBRL'))
    return rows

def collect_feed(fetch,name,url):
    body=fetch.get(url)
    if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():raise CollectionError('Unsafe XML declarations')
    root=ElementTree.fromstring(body);rows=[]
    for item in root.findall('./channel/item')[:15]:
        link=item.findtext('link','').strip();u=urlsplit(link)
        if u.scheme!='https' or u.hostname!='www.federalreserve.gov':continue
        pub=parsedate_to_datetime(item.findtext('pubDate',''))
        if pub.tzinfo is None or pub>datetime.now(timezone.utc):continue
        meta={}
        if len(rows)<2:
            try:meta['excerpts']=excerpts(fetch.get(link))
            except CollectionError as exc:meta['document_error']=str(exc)
        rows.append(event(name,item.findtext('guid') or link,item.findtext('title','').strip(),link,pub.astimezone(timezone.utc).isoformat(),metadata=meta,institution='Federal Reserve',claim='opinion' if name=='fed_speeches' else 'primary_evidence'))
    return rows

def resolve_symbol(store,symbol):
    if symbol in CIKS:return CIKS[symbol]
    configured=json.loads(os.getenv('RADAR_CIK_MAP','{}'))
    if symbol in configured and re.fullmatch(r'\d{10}',configured[symbol]):return configured[symbol]
    # Official mappings only, no ticker-to-company guessing.
    data=Fetch(time.monotonic()+15).json('https://www.sec.gov/files/company_tickers.json')
    for company in data.values():
        if company.get('ticker')==symbol:return str(company['cik_str']).zfill(10)
    raise CollectionError('Company ticker not found in official SEC mapping')

def run(store):
    owner=str(uuid.uuid4())
    if not store.rpc('radar_claim_collection',{'p_owner':owner}):return {'status':'cooldown_or_running','records':0}
    deadline=time.monotonic()+190;fetch=Fetch(deadline);now=datetime.now(timezone.utc).isoformat()
    try:
        previous=store.request('radar_status',query='select=*&id=eq.collector&limit=1')
        state=previous[0]['payload'] if previous else {};jobs={j['name']:j for j in state.get('jobs',[])}
        private=store.request('radar_watchlists',query='select=symbol&order=created_at.asc&limit=400')
        universe=list(dict.fromkeys(['AAPL','MSFT','NVDA']+[r['symbol'] for r in private]))
        selected=sorted(universe,key=lambda s:jobs.get('sec:'+s,{}).get('last_attempt') or jobs.get('sec:'+s,{}).get('last_success') or '')[:3]
        total=0
        tasks=[('sec:'+s,s) for s in selected]+[(name,None) for name in FEEDS]
        for name,symbol in tasks:
            old=jobs.get(name,{})
            try:
                records=collect_company(fetch,symbol,resolve_symbol(store,symbol)) if symbol else collect_feed(fetch,name,FEEDS[name])
                for i in range(0,len(records),25):store.request('radar_events',rows=records[i:i+25])
                total+=len(records);jobs[name]={'name':name,'status':'success','last_success':datetime.now(timezone.utc).isoformat(),'last_attempt':now,'last_error':None,'records':len(records)}
            except Exception as exc:
                error=str(exc) if isinstance(exc,CollectionError) else type(exc).__name__
                jobs[name]={'name':name,'status':'error','last_success':old.get('last_success'),'last_attempt':now,'last_error':error,'records':0}
        state.update({'jobs':list(jobs.values()),'watchlist':['AAPL','MSFT','NVDA'],'active_company_count':len(universe),'cadence':'daily_scheduled','batch_size':3,
                      'collection_note':'Daily free-tier schedule; up to three companies per run, rotated by oldest successful collection.',
                      'last_run_records':total})
        store.request('radar_status',rows=[{'id':'collector','updated_at':datetime.now(timezone.utc).isoformat(),'payload':state}])
        store.finish_collection(owner,None if total else 'No source records retrieved')
        return {'status':'complete' if total else 'source_failure','records':total,'companies':selected}
    except Exception:
        store.finish_collection(owner,'Collector failed; inspect source health')
        raise
