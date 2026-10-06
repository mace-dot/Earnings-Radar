"""Alpaca news metadata only; entitled access/retention must be confirmed by user."""
import os
from earnings_radar.providers.base import HTTP, Event, ProviderError
from earnings_radar.validation import utc_timestamp

def alpaca_headers():
    if not all(os.getenv(k) for k in ('ALPACA_API_KEY','ALPACA_API_SECRET')):
        raise ProviderError('Alpaca key and secret not configured')
    return {'APCA-API-KEY-ID':os.environ['ALPACA_API_KEY'],'APCA-API-SECRET-KEY':os.environ['ALPACA_API_SECRET']}

class AlpacaNews:
    def __init__(self,http=None): self.http=http or HTTP()
    def collect(self,tickers,checkpoint=None):
        import json
        state=json.loads(checkpoint or '{}')
        params={'symbols':','.join(tickers),'limit':50,'include_content':'false','sort':'asc'}
        if state.get('page_token'): params['page_token']=state['page_token']
        if state.get('start'): params['start']=state['start']
        data=self.http.get_json('https://data.alpaca.markets/v1beta1/news',headers=alpaca_headers(),params=params)
        events=[]
        for item in data.get('news',[]):
            events.append(Event('alpaca_news',str(item['id']),item['url'],item['headline'],utc_timestamp(item['created_at']),tuple(item.get('symbols',[])),provenance='secondary',access_category='licensed_metadata',claim_type='secondary_reporting',author=item.get('author',''),institution=item.get('source',''),metadata={'updated_at':item.get('updated_at')}))
        # Continue bounded pagination across jobs, preserving query interval.
        token=data.get('next_page_token')
        next_state={'page_token':token,'start':state.get('start')} if token else {'start':max([e.metadata.get('updated_at') or e.published_at for e in events],default=state.get('start'))}
        return events,json.dumps(next_state)
