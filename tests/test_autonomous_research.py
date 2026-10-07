import datetime as dt
import pytest
from web.api._directory import parse_index
from web.api._orchestrator import valid_symbol
from web.api._assistant import validate_model,deterministic
from web.api._collector import CollectionError

def test_discovery_rejects_unknown_archive_paths_and_other_days():
    body=b'CIK|Company Name|Form Type|Date Filed|File Name\n1|A|10-Q|2026-10-06|edgar/data/1/0000000001-26-000001.txt\n1|A|10-Q|2026-10-05|edgar/data/1/0000000001-26-000001.txt\n1|A|10-Q|2026-10-06|https://evil.test/file\n'
    rows=parse_index(body,dt.date(2026,10,6))
    assert len(rows)==1 and rows[0]['cik']=='0000000001'
    with pytest.raises(CollectionError):parse_index(b'blocked',dt.date(2026,10,6))

def test_model_sources_must_exist_and_quotes_must_match():
    rows=[{'id':'a','title':'Reported cash declined','url':'https://www.sec.gov/test','evidence_meta':{}}]
    payload={'answer':'Cash declined; review the filing.','citations':[{'evidence_id':'a','quote':'Reported cash declined'}],'invalidation':[]}
    assert validate_model(payload,rows)['citations'][0]['url']==rows[0]['url']
    payload['citations'][0]['quote']='Guaranteed 90% winning call'
    with pytest.raises(ValueError):validate_model(payload,rows)
    payload['citations'][0]={'evidence_id':'missing','quote':'Reported cash declined'}
    with pytest.raises(ValueError):validate_model(payload,rows)

def test_empty_evidence_never_produces_a_pick():
    result=deterministic({'events':[]},'Which call should I buy?')
    assert result['citations']==[] and 'No financial conclusion' in result['answer']
    assert valid_symbol('BRK-B') and not valid_symbol('AAPL&select=*')
