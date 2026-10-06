"""Explicitly allowlisted official RSS metadata; no crawling or full article copying."""
from email.utils import parsedate_to_datetime
from datetime import timezone
from urllib.parse import urlsplit
from defusedxml import ElementTree
from earnings_radar.providers.base import HTTP, Event, ProviderError

FEEDS = {'fed_press': 'https://www.federalreserve.gov/feeds/press_all.xml', 'fed_speeches':'https://www.federalreserve.gov/feeds/speeches.xml'}

def parse_rss(body, provider):
    root=ElementTree.fromstring(body)
    events=[]
    for item in root.findall('./channel/item')[:50]:
        url=item.findtext('link','').strip()
        if urlsplit(url).hostname != 'www.federalreserve.gov' or urlsplit(url).scheme != 'https':
            raise ProviderError('unexpected official feed link')
        stamp=parsedate_to_datetime(item.findtext('pubDate',''))
        if stamp.tzinfo is None:
            raise ProviderError('RSS publication time lacks timezone')
        title=item.findtext('title','').strip()
        if not title or not url: continue
        events.append(Event(provider,item.findtext('guid') or url,url,title,stamp.astimezone(timezone.utc).isoformat(),institution='Federal Reserve',claim_type='opinion' if provider=='fed_speeches' else 'primary_evidence'))
    return events

class OfficialFeeds:
    def __init__(self,http=None): self.http=http or HTTP()
    def collect(self,name):
        return parse_rss(self.http.request('GET',FEEDS[name]),name)
