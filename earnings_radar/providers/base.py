"""Bounded HTTPS requests; external content cannot select hosts or execute tools."""
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from datetime import datetime, timezone
import time
import requests

ALLOWED_HOSTS = {'data.sec.gov','www.sec.gov','www.federalreserve.gov','data.alpaca.markets','api.anthropic.com','api.telegram.org'}
class ProviderError(RuntimeError):
    pass

@dataclass(frozen=True)
class Event:
    provider: str
    event_id: str
    url: str
    title: str
    published_at: str
    tickers: tuple[str,...] = ()
    provenance: str = 'primary'
    access_category: str = 'public_metadata'
    claim_type: str = 'primary_evidence'
    author: str = ''
    institution: str = ''
    metadata: dict = field(default_factory=dict)

class HTTP:
    def __init__(self, user_agent='EarningsRadar/0.2 personal-research', session=None):
        self.session = session or requests.Session()
        self.user_agent = user_agent
        self.last_request = 0.0

    def request(self, method, url, *, headers=None, params=None, json=None, max_bytes=5_000_000):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):
            raise ProviderError('destination is not allowlisted HTTPS')
        delay = 0.25-(time.monotonic()-self.last_request)
        if delay > 0:
            time.sleep(delay)  # Max 4 requests/second, below SEC's 10/sec limit.
        self.last_request = time.monotonic()
        try:
            with self.session.request(method,url,headers={'User-Agent':self.user_agent,**(headers or {})},params=params,json=json,timeout=(5,20),allow_redirects=False,stream=True) as response:
                if response.status_code != 200:
                    raise ProviderError(f'{parsed.hostname}: HTTP {response.status_code}')
                chunks=[]; size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size > max_bytes:
                        raise ProviderError(f'response exceeds {max_bytes//1_000_000} MB limit')
                    chunks.append(chunk)
                return b''.join(chunks)
        except requests.RequestException:
            # Requests exceptions can contain URLs with credentials; do not log them.
            raise ProviderError(f'{parsed.hostname}: connection failed') from None

    def get_json(self,url,**kwargs):
        import json
        return json.loads(self.request('GET',url,**kwargs))
