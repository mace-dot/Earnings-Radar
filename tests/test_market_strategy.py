from datetime import datetime,timezone,timedelta
import math
import pytest
from web.api._market import validate_bars,refresh
from web.api._price_statistics import summarize
from web.api._sources import readable
from web.api._strategy import assess
from web.api._news import parse_feed
from web.api._collector import CollectionError

def bars(n=100):
 day=datetime(2026,1,1,tzinfo=timezone.utc);rows=[]
 while len(rows)<n:
  if day.weekday()<5:
   price=100+len(rows)*.3+math.sin(len(rows))
   rows.append({'t':day.replace(hour=14).isoformat(),'o':price,'h':price+2,'l':price-2,'c':price+1,'v':10000})
  day+=timedelta(days=1)
 return rows

def test_price_validation_order_duplicates_and_incomplete_session():
 rows=bars();normalized=validate_bars(rows)
 assert len(normalized)==100 and normalized[0]['session']=='2026-01-01'
 with pytest.raises(ValueError):validate_bars(rows+[rows[0]])
 with pytest.raises(ValueError):validate_bars([{**rows[0],'c':float('nan')}])
 with pytest.raises(ValueError):validate_bars([{**rows[0],'o':1000}])
 now=datetime(2026,10,7,15,tzinfo=timezone.utc)
 assert validate_bars([{'t':'2026-10-07T04:00:00Z','o':100,'h':102,'l':99,'c':101,'v':1}],now)==[]

def test_statistics_use_same_feed_and_do_not_create_odds():
 q=summarize(bars())
 assert q['status']=='available' and q['momentum_20']>0
 assert q['volume_ratio_20']==1 and q['parkinson_volatility_20']>0
 assert not any(k in q for k in ('probability','win_rate','price_target'))
 assert summarize(bars(20))['status']=='insufficient_history'

def test_evidence_uses_human_filing_index_not_raw_json():
 e={'id':'a','provider':'sec_fundamentals','title':'raw','url':'https://data.sec.gov/api/xbrl/companyconcept/CIK0001318605/us-gaap/NetIncomeLoss.json','tickers':['TSLA'],'evidence_meta':{'accession':'0001318605-26-000001','tag':'NetIncomeLoss','value':123,'end':'2026-06-30'}}
 r=readable(e)
 assert r['readable_url']=='https://www.sec.gov/Archives/edgar/data/1318605/000131860526000001/0001318605-26-000001-index.htm'
 assert r['display_value']=='$123' and 'Net profit' in r['display_title']

def result(price=False):
 e={'id':'a','title':'Revenue increased','url':'https://www.sec.gov/filing','published_at':'2026-08-01T00:00:00Z','evidence_meta':{'tag':'RevenueFromContractWithCustomerExcludingAssessedTax','end':'2026-06-30'},'research':{'calculations':[{'label':'Year-over-year change','value':15,'evidence_ids':['a','b']}]}}
 return {'company':{'symbol':'TEST'},'events':[e],'financial_context':{'TEST':[]},'price_history':{'status':'available','statistics':summarize(bars())} if price else {}}

def test_selected_direction_can_be_rejected_without_blocking_research():
 up=assess(result(),'up');down=assess(result(),'down')
 assert up['decision']=='WATCH' and down['decision']=='WAIT'
 assert up['supporting'] and down['counterevidence']
 assert up['contract_decision']=='WAIT' and up['scenarios'] is None
 assert up['citations'][0]['evidence_id']=='a'
 with pytest.raises(ValueError):assess(result(),'sell naked calls')

def test_statistical_ranges_are_sensitivity_scenarios_not_forecasts():
 r=assess(result(True),'up')
 assert len(r['scenarios'])==2
 assert all(s['lower']<s['reference_price']<s['upper'] for s in r['scenarios'])
 assert 'not a confidence interval' in r['scenarios'][0]['method']

def test_rss_is_reporting_not_primary_fact_and_rejects_unsafe_links():
 body=b'<rss><channel><item><title>Company raises outlook</title><link>https://finance.yahoo.com/news/story</link><pubDate>Tue, 06 Oct 2026 12:00:00 GMT</pubDate></item><item><title>Bad</title><link>https://evil.example/x</link><pubDate>Tue, 06 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
 rows=parse_feed(body,'yahoo_rss','Yahoo Finance',{'finance.yahoo.com'},'secondary','TSLA',datetime(2026,10,7,tzinfo=timezone.utc))
 assert len(rows)==1 and rows[0]['provenance']=='secondary'
 assert rows[0]['claim_type']=='reporting' and not rows[0]['evidence_meta']['full_article_collected']
 with pytest.raises(CollectionError):parse_feed(b'<!DOCTYPE rss><rss/>','x','X',set(),'secondary')

def test_missing_credentials_never_fabricate_or_refresh_prices(monkeypatch):
 monkeypatch.delenv('ALPACA_API_KEY',raising=False);monkeypatch.delenv('ALPACA_API_SECRET',raising=False)
 class Store:
  def request(self,*args,**kwargs):return []
  def rpc(self,*args,**kwargs):raise AssertionError('No provider job without credentials')
 r=refresh(Store(),'AAPL');assert r['status']=='not_configured' and r['bars']==[]

def test_provider_failure_does_not_replace_usable_cache(monkeypatch):
 monkeypatch.setenv('RADAR_MARKET_DISPLAY_AUTHORIZED','true')
 import web.api._market as market
 monkeypatch.setenv('ALPACA_API_KEY','fixture-key');monkeypatch.setenv('ALPACA_API_SECRET','fixture-secret')
 def fail(symbol):raise market.MarketError('Provider unavailable')
 monkeypatch.setattr(market,'collect_alpaca',fail)
 payload={'bars':[{'session':'2026-10-06','c':100}], 'retrieved_at':'2026-10-07T00:00:00+00:00','statistics':{'status':'insufficient_history'}}
 class Store:
  patch=None
  def rpc(self,*args,**kwargs):return True
  def request(self,*args,**kwargs):
   if kwargs.get('method')=='PATCH':self.patch=kwargs['rows'];return None
   return [{'payload':payload,'last_error':'Provider unavailable'}]
 s=Store();r=refresh(s,'AAPL')
 assert r['bars']==payload['bars'] and 'payload' not in s.patch
 assert s.patch['last_error']=='Provider unavailable'

def test_current_ratio_uses_matched_balance_periods():
 from web.api._research import financial_context
 def fact(tag,value,end):return {'id':tag+end,'tickers':['TEST'],'published_at':'2026-08-01T00:00:00Z','evidence_meta':{'tag':tag,'value':value,'end':end,'units':'USD'}}
 rows=[fact('AssetsCurrent',100,'2026-06-30'),fact('LiabilitiesCurrent',200,'2026-06-30'),fact('AssetsCurrent',500,'2025-12-31')]
 ratios=financial_context(rows,'TEST')
 current=next(r for r in ratios if r['label']=='Current ratio')
 assert current['value']==.5 and len(current['evidence_ids'])==2
 assert current['period_end']=='2026-06-30'
