"""One conservative, event-aware selector for dashboard, exports and candidates."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import os
from functools import lru_cache
import exchange_calendars as xcals
import pandas as pd
from earnings_radar.validation import validate_quote, iso_date

NY = ZoneInfo('America/New_York')
LIVE_MAX_AGE = float(os.getenv('LIVE_QUOTE_MAX_AGE_SECONDS', '60'))
SYNC_TOLERANCE = float(os.getenv('QUOTE_SYNC_TOLERANCE_SECONDS', '5'))

@lru_cache(maxsize=8)
def calendar(year):
    return xcals.get_calendar("XNYS", start=f"{year-1}-01-01", end=f"{year+2}-12-31")

def cutoff(day):
    cal = calendar(int(iso_date(day)[:4]))
    session = cal.date_to_session(pd.Timestamp(iso_date(day)), direction='previous')
    return cal.session_close(session).to_pydatetime()

def event_boundary(event):
    day = iso_date(event['earnings_date'])
    timing = event.get('earnings_time','Unknown')
    cal = calendar(int(day[:4]))
    session = cal.date_to_session(pd.Timestamp(day), direction='next')
    if timing == 'BMO':
        return cal.session_open(session).to_pydatetime()
    if timing in {'AMC','During Market','Unknown'}:
        # Conservative unknown/intraday boundary: must survive that day's close.
        return cutoff(day)
    raise ValueError('invalid earnings timing')

def rejection_reasons(quote, event, *, now=None, live=False):
    now = now or datetime.now(timezone.utc)
    try:
        q = validate_quote(quote, now=now)
        close = cutoff(q['expiration'])
        boundary = event_boundary(event)
    except (TypeError, ValueError, OverflowError) as exc:
        return ['invalid_quote:'+str(exc)]
    reasons = []
    if close <= boundary:
        reasons.append('expiration_does_not_survive_event')
    if close <= now:
        reasons.append('expired')
    if q.get('adjusted') or q['multiplier'] != 100:
        reasons.append('unsupported_deliverables')
    if any(q.get(k) is None for k in ('stock_price','call_bid','call_ask','put_bid','put_ask','quote_timestamp')):
        reasons.append('missing_fields')
    if live:
        if event.get('earnings_time') == 'Unknown':
            reasons.append('unknown_announcement_time')
        if event.get('confirmation_status') != 'Confirmed':
            reasons.append('unconfirmed_schedule')
        if q['feed_type'] != 'live':
            reasons.append('feed_not_live')
        keys = ('underlying_timestamp','call_timestamp','put_timestamp')
        if any(not q.get(k) for k in keys):
            reasons.append('unsynchronized_quotes')
        else:
            stamps = [datetime.fromisoformat(q[k]) for k in keys]
            if (max(stamps)-min(stamps)).total_seconds() > SYNC_TOLERANCE:
                reasons.append('unsynchronized_quotes')
            if any((now-ts).total_seconds() > LIVE_MAX_AGE for ts in stamps):
                reasons.append('stale_quote')
        if not q.get('call_contract_id') or not q.get('put_contract_id'):
            reasons.append('missing_contract_identity')
    elif q.get('quote_timestamp') and (now-datetime.fromisoformat(q['quote_timestamp'])).total_seconds() > 86400:
        reasons.append('stale_quote')
    return reasons

def select_quote(event, quotes, *, now=None, live=False):
    now = now or datetime.now(timezone.utc)
    latest = {}
    for q in quotes:
        if q.get('ticker') != event.get('ticker'):
            continue
        try:
            ts = datetime.fromisoformat(validate_quote(q, now=now)['quote_timestamp'])
        except (TypeError, ValueError):
            continue
        if ts > now:
            continue
        key = (q.get('call_contract_id') or q.get('strike'),q.get('put_contract_id') or q.get('strike'),q.get('expiration'),q.get('source'),q.get('feed_type','historical'))
        if key not in latest or (ts,q.get('id',0)) > latest[key][0]:
            latest[key] = ((ts,q.get('id',0)),q)
    eligible = [q for _,q in latest.values() if not rejection_reasons(q,event,now=now,live=live)]
    if not eligible:
        return None
    return min(eligible,key=lambda q:(-datetime.fromisoformat(q['quote_timestamp']).timestamp(),abs(q['strike']-q['stock_price']),q['expiration']))
