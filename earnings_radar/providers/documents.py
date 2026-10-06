"""Bounded SEC HTML excerpts with source offsets. External text is never executed."""
from html.parser import HTMLParser
import hashlib
import json
from earnings_radar.providers.base import Event,ProviderError

class FilingText(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}:self.skip+=1
        if tag=='br' and not self.skip:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style'}:self.skip=max(0,self.skip-1)
        if tag in {'p','div','tr','li','h1','h2','h3'} and not self.skip:self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def extract(body):
    if b'<html' not in body.lower():raise ProviderError('only bounded HTML filing documents supported')
    parser=FilingText();parser.feed(body.decode('utf-8',errors='replace'))
    paragraphs=[' '.join(p.split()) for p in ''.join(parser.parts).split('\n') if p.strip()]
    text='\n'.join(paragraphs)
    terms=('revenue','guidance','outlook','margin','net income','net loss','liquidity','risk','cash flow','results of operations')
    excerpts=[];offset=0
    for paragraph in paragraphs:
        if any(term in paragraph.lower() for term in terms) and len(paragraph)>=40:
            excerpt=paragraph[:1200]
            excerpts.append({'text':excerpt,'start':offset,'end':offset+len(excerpt)})
        offset+=len(paragraph)+1
        if len(excerpts)>=8:break
    return {'body_sha256':hashlib.sha256(body).hexdigest(),'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'parser_version':'sec-html-excerpts-v1','excerpts':excerpts,'limitations':'Exact excerpts in normalized filing text; not full transcript coverage or automated verification of management assertions.'}

def collect(parent,http):
    if parent['provider']!='sec' or not parent['url'].startswith('https://www.sec.gov/Archives/edgar/data/'):
        raise ProviderError('document collection only supports SEC submission references')
    metadata=extract(http.request('GET',parent['url'],max_bytes=20_000_000))
    metadata['parent_evidence_id']=parent['id']
    return Event('sec_document',parent['provider_event_id'],parent['url'],parent['title']+' — primary document excerpts',parent['published_at'],tuple(json.loads(parent['tickers'])),institution='SEC filing issuer',metadata=metadata)
