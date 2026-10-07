from datetime import datetime,timezone
from unittest.mock import patch
import json
import threading
from http.server import HTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
from web.api._research import interpretation,financial_context,enrich
from web.api._collector import event,collect_feed,excerpts,run,CollectionError
from web.api.index import handler

NOW=datetime(2026,10,6,tzinfo=timezone.utc)
def fact(tag,value,start,end,published='2026-10-05T12:00:00+00:00',symbol='AAPL'):
 return event('sec_fundamentals',f'{symbol}:{tag}:{start}:{end}',f'{symbol} result','https://data.sec.gov/test',published,[symbol],{'tag':tag,'value':value,'start':start,'end':end,'units':'USD'})

def test_growth_calculation_references_comparable_periods_only():
 a=fact('NetIncomeLoss',100,'2026-07-01','2026-09-30');b=fact('NetIncomeLoss',80,'2025-07-01','2025-09-30')
 wrong=fact('NetIncomeLoss',1,'2025-01-01','2025-12-31')
 r=interpretation(a,[a,b,wrong],NOW)
 assert r['calculations'][0]['value']==25
 assert r['calculations'][0]['evidence_ids']==[a['id'],b['id']]
 assert r['contrarian_status']=='unverified'
 assert 'conditional' not in r['facts'][0]['text']

def test_margins_reject_mismatched_periods():
 a=fact('RevenueFromContractWithCustomerExcludingAssessedTax',100,'2026-07-01','2026-09-30')
 b=fact('NetIncomeLoss',20,'2026-07-01','2026-09-30');c=fact('GrossProfit',50,'2026-01-01','2026-09-30')
 ratios=financial_context([a,b,c],'AAPL')
 assert len(ratios)==1;assert ratios[0]['value']==20
 assert set(ratios[0]['evidence_ids'])=={a['id'],b['id']}

def test_old_or_future_evidence_not_weekly_candidate():
 for published in ('2020-01-01T00:00:00+00:00','2027-01-01T00:00:00+00:00'):
  a=fact('GrossProfit',50,'2026-07-01','2026-09-30',published)
  assert not interpretation(a,[a],NOW)['ranking']['eligible_weekly']

def test_speeches_distinguished_from_policy_and_html_never_executed():
 e=event('fed_speeches','speech','Monetary policy','https://www.federalreserve.gov/test','2026-10-05T12:00:00+00:00',claim='opinion')
 assert 'not an enacted policy' in interpretation(e,[e],NOW)['takeaway']
 result=excerpts(b'<html><script>revenue = steal_credentials()</script><p>Revenue rose in the reported period, but margin effects require review.</p></html>')
 assert len(result)==1 and 'steal_credentials' not in result[0]['text']

def test_external_entities_rejected():
 class Fetch:
  def get(self,url):return b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss/>'
 with pytest.raises(CollectionError):collect_feed(Fetch(),'fed_press','https://www.federalreserve.gov/test')

def test_lease_prevents_duplicate_collection():
 class Fake:
  def rpc(self,*args):return False
 assert run(Fake())['status']=='cooldown_or_running'

def test_cross_site_watchlist_write_rejected_before_database_access():
 server=HTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  req=Request(f'http://127.0.0.1:{server.server_port}/api/watchlist',data=b'{"symbol":"AAPL","action":"add"}',headers={'Origin':'https://evil.example','Content-Type':'application/json'})
  with pytest.raises(HTTPError) as exc:urlopen(req)
  assert exc.value.code==403
 finally:server.shutdown();server.server_close();thread.join()

def test_fed_metadata_claims_do_not_become_verified_policy_direction():
 e=event('fed_press','news','Interest rates update','https://www.federalreserve.gov/test','2026-10-05T12:00:00+00:00')
 r=interpretation(e,[e],NOW)
 assert r['contrarian_status']=='unverified'
 assert 'could' in r['bull'][0] and 'could' in r['bear'][0]
 assert not r['ranking']['eligible_weekly']  # Headline alone lacks financial comparison or excerpts.
