"""Public XBRL company-concept facts; filing-date precision is explicitly recorded."""
from datetime import datetime,timezone
import math
from earnings_radar.providers.base import Event
from earnings_radar.providers.sec import SEC

TAGS=('RevenueFromContractWithCustomerExcludingAssessedTax','NetIncomeLoss','GrossProfit')

class SECFundamentals(SEC):
    def collect(self,ticker,cik):
        # SEC parent validates contact and request construction; CIKs are seeded/explicit.
        import re
        from earnings_radar.providers.base import ProviderError
        if not re.fullmatch(r'\d{10}',cik):raise ProviderError('CIK must have 10 digits')
        events=[]
        now=datetime.now(timezone.utc)
        for tag in TAGS:
            url=f'https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json'
            try:data=self.http.get_json(url)
            except ProviderError as exc:
                if str(exc).endswith('HTTP 404'):continue  # Tag genuinely absent; not a zero metric.
                raise
            values=data.get('units',{}).get('USD',[])
            by_period={}
            for fact in values:
                if fact.get('form') not in ('10-Q','10-K','10-Q/A','10-K/A') or not fact.get('start') or not fact.get('end'):continue
                start=datetime.fromisoformat(fact['start']);end=datetime.fromisoformat(fact['end'])
                duration=(end-start).days
                if not (70<=duration<=105 or 350<=duration<=380):continue
                if not isinstance(fact.get('val'),(int,float)) or not math.isfinite(fact['val']):continue
                filed=datetime.fromisoformat(fact['filed']).replace(tzinfo=timezone.utc)
                # Date-only publication is bounded conservatively to end-of-day, never intraday precision.
                published=filed.replace(hour=23,minute=59,second=59)
                if published>now:continue
                key=(fact['start'],fact['end'])
                if key not in by_period or (fact['filed'],fact['accn'])>(by_period[key]['filed'],by_period[key]['accn']):by_period[key]=fact
            for (start,end),fact in sorted(by_period.items(),key=lambda kv:kv[0][1],reverse=True)[:4]:
                published=datetime.fromisoformat(fact['filed']).replace(hour=23,minute=59,second=59,tzinfo=timezone.utc).isoformat()
                title=f"{ticker}: {tag} {fact['val']:,.0f} USD for {start} to {end}"
                metadata={'tag':tag,'value':fact['val'],'units':'USD','start':start,'end':end,'filed':fact['filed'],'accession':fact['accn'],'fiscal_year':fact.get('fy'),'fiscal_period':fact.get('fp'),'publication_precision':'filing_date_end_of_day_bound','not_consensus':True}
                events.append(Event('sec_fundamentals',f'{ticker}:{tag}:{start}:{end}',url,title,published,(ticker,),institution='SEC XBRL',metadata=metadata))
        return events
