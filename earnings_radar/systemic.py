"""Independent dimensions, age/frequency checks and unknowns, never crash odds."""
from datetime import datetime

LIMITS={'volatility':(30,'above'),'credit_spread_bps':(500,'above'),'breadth_pct':(30,'below')}
DIMENSIONS=('volatility','credit_spread_bps','breadth_pct','banking_exposure','funding')

def assess(observations,now):
    dimensions={}; concerns=[]
    for name in DIMENSIONS:
        row=observations.get(name)
        if not row:
            dimensions[name]={'status':'unknown','reason':'data unavailable'};continue
        age=(now-datetime.fromisoformat(row['published_at'])).total_seconds()
        if age < 0 or age>row['max_age_seconds']:
            dimensions[name]={'status':'unknown','reason':'stale or future release'};continue
        if name not in LIMITS:
            dimensions[name]={'status':'context_only','frequency':row['frequency']};continue
        limit,direction=LIMITS[name]
        concerning=row['value']>limit if direction=='above' else row['value']<limit
        dimensions[name]={'status':'concerning' if concerning else 'within_configured_threshold','value':row['value'],'frequency':row['frequency'],'evidence_id':row['evidence_id']}
        if concerning:concerns.append(name)
    return {'scope':'market-wide','dimensions':dimensions,'concerns':concerns,'conclusion':'Review exposure' if len(concerns)>=2 else 'Insufficient independent evidence for an aggregate risk conclusion','probability':None}
