"""SEC submissions metadata; filings are not an earnings-calendar forecast."""
from datetime import datetime, timezone
import re
from earnings_radar.providers.base import Event, ProviderError, HTTP

CIKS = {'AAPL':'0000320193','MSFT':'0000789019','NVDA':'0001045810'}

class SEC:
    def __init__(self, user_agent, http=None):
        if not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',user_agent):
            raise ProviderError('SEC_USER_AGENT requires your organization/name and real contact email')
        self.http = http or HTTP(user_agent)

    def collect(self, ticker, cik):
        if not re.fullmatch(r'\d{10}',cik):
            raise ProviderError('CIK must have 10 digits')
        data=self.http.get_json(f'https://data.sec.gov/submissions/CIK{cik}.json')
        recent=data.get('filings',{}).get('recent',{})
        result=[]
        for i,accession in enumerate(recent.get('accessionNumber',[])[:50]):
            form=recent['form'][i]
            if form not in {'8-K','8-K/A','10-Q','10-K','10-Q/A','10-K/A'}:
                continue
            document=recent['primaryDocument'][i]
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',document) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession):
                continue
            # acceptanceDateTime is the publication timestamp. Missing timezone is explicitly UTC per SEC format.
            accepted=recent.get('acceptanceDateTime',[])[i]
            dt=datetime.fromisoformat(accepted.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            result.append(Event('sec',accession,f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{document}',f'{ticker} filed {form}',dt.astimezone(timezone.utc).isoformat(),(ticker,),institution='SEC',metadata={'cik':cik,'form':form,'report_date':recent.get('reportDate',[])[i], 'amendment':form.endswith('/A')}))
        return result
