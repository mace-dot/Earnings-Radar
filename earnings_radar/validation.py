"""Shared strict input validation. Naive timestamps are rejected, never guessed."""
from datetime import date, datetime, timezone, timedelta
import math
import re
import pandas as pd

FUTURE_TOLERANCE = timedelta(seconds=60)

def missing(value):
    return value is None or (isinstance(value, str) and not value.strip()) or bool(pd.isna(value))

def text(value, default=''):
    return default if missing(value) else str(value).strip()

def number(value, *, integer=False, positive=False):
    if missing(value):
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError('numeric values must be finite and nonnegative (positive for strike/spot)')
    if integer and not result.is_integer():
        raise ValueError('counts must be whole numbers')
    return int(result) if integer else result

def iso_date(value):
    value = text(value)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('date must be exactly YYYY-MM-DD')
    return date.fromisoformat(value).isoformat()

def utc_timestamp(value, *, now=None, allow_future=False):
    if missing(value):
        return None
    dt = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timestamp requires an explicit timezone')
    dt = dt.astimezone(timezone.utc)
    if not allow_future and dt > (now or datetime.now(timezone.utc)) + FUTURE_TOLERANCE:
        raise ValueError('timestamp exceeds 60 second future tolerance')
    return dt.isoformat()

def ticker(value):
    value = text(value).upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9_.-]{0,19}', value):
        raise ValueError('invalid ticker')
    return value

def validate_quote(row, *, now=None):
    out = dict(row)
    out['ticker'] = ticker(row.get('ticker'))
    out['strike'] = number(row.get('strike'), positive=True)
    if out['strike'] is None:
        raise ValueError('strike is required')
    out['expiration'] = iso_date(row.get('expiration'))
    for key in ('stock_price', 'call_bid', 'call_ask', 'put_bid', 'put_ask'):
        out[key] = number(row.get(key), positive=key == 'stock_price')
    for key in ('call_volume', 'put_volume', 'call_open_interest', 'put_open_interest'):
        out[key] = number(row.get(key), integer=True)
    for side in ('call', 'put'):
        bid, ask = out[side+'_bid'], out[side+'_ask']
        if bid is not None and ask is not None and bid > ask:
            raise ValueError('crossed '+side+' quote')
    for key in ('quote_timestamp', 'underlying_timestamp', 'call_timestamp', 'put_timestamp'):
        out[key] = utc_timestamp(row.get(key), now=now)
    out['multiplier'] = number(row.get('multiplier', 100), integer=True, positive=True)
    if out['multiplier'] is None:
        raise ValueError('multiplier required')
    out['feed_type'] = text(row.get('feed_type'), 'historical')
    if out['feed_type'] not in {'live', 'delayed', 'indicative', 'historical', 'sample'}:
        raise ValueError('invalid feed type')
    adjusted=number(row.get('adjusted',0),integer=True)
    if adjusted not in (0,1):raise ValueError('adjusted must be 0 or 1')
    out['adjusted']=adjusted
    for kind,letter in (('call','C'),('put','P')):
        identity=text(row.get(kind+'_contract_id'))
        if identity:
            match=re.fullmatch(r'([A-Z]{1,6})([0-9]{6})([CP])([0-9]{8})',identity)
            expected=date.fromisoformat(out['expiration']).strftime('%y%m%d')
            if not match or match[1]!=out['ticker'].replace('.','') or match[2]!=expected or match[3]!=letter or int(match[4])/1000!=out['strike']:
                raise ValueError('contract identity does not match ticker/type/strike/expiration')
        out[kind+'_contract_id']=identity or None
    out['source'] = text(row.get('source'))
    return out
