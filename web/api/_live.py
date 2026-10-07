"""Bounded IEX quotes with shared leases; never confuse charts with model inputs."""
import json, math, os, re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, build_opener
try:
    from ._market import NoRedirect, MarketError
    from ._policy import POLICY
except ImportError:
    from _market import NoRedirect, MarketError
    from _policy import POLICY


def enabled():
    return os.getenv('RADAR_MARKET_DISPLAY_AUTHORIZED', 'false').lower() == 'true'


def provider_get(path, params):
    key, secret = os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_API_SECRET')
    if not key or not secret: raise MarketError('Provider credentials are unavailable')
    url = 'https://data.alpaca.markets' + path + '?' + urlencode(params)
    try:
        req = Request(url, headers={'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret})
        with build_opener(NoRedirect()).open(req, timeout=12) as response:
            body = response.read(1_500_001)
        if len(body) > 1_500_000: raise MarketError('Provider response exceeded bound')
        return json.loads(body)
    except MarketError: raise
    except Exception: raise MarketError('Provider request failed; cached research is preserved') from None


def quote_payload(symbol, data, now=None):
    now = now or datetime.now(timezone.utc)
    q = data.get('quotes', {}).get(symbol)
    if not isinstance(q, dict): raise ValueError('No quote for this instrument')
    t = datetime.fromisoformat(q['t'].replace('Z', '+00:00'))
    if t.tzinfo is None: raise ValueError('Quote requires a timezone')
    age = (now - t).total_seconds()
    bid, ask = float(q['bp']), float(q['ap'])
    sizes = [float(q[k]) for k in ('bs', 'as')]
    if age < -2 or not all(math.isfinite(v) and v > 0 for v in [bid, ask]+sizes) or bid > ask:
        raise ValueError('Invalid or crossed quote')
    return {'symbol': symbol, 'bid': bid, 'ask': ask, 'mid': (bid+ask)/2,
            'bid_size': sizes[0], 'ask_size': sizes[1], 'observed_at': t.isoformat(),
            'retrieved_at': now.isoformat(), 'age_seconds': max(0, age),
            'provider': 'Alpaca', 'feed': 'IEX', 'scope': 'IEX venue; not a consolidated best bid/offer',
            'status': 'fresh_quote' if age <= POLICY['stock_quote_max_age_seconds'] else 'stale',
            'session_status': 'unverified', 'entry_eligible': False,
            'reason': 'Exchange-session status and instrument eligibility require verification before entry.'}


def live_quote(store, symbol):
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,14}', symbol): raise ValueError('Invalid ticker')
    if not enabled(): return {'status': 'authorization_required', 'symbol': symbol,
        'reason': 'Provider authentication works; public price use is not yet confirmed.', 'entry_eligible': False}
    directory = store.request('radar_universe', query='select=active&symbol=eq.'+symbol+'&limit=1')
    if not directory or not directory[0]['active']: raise ValueError('Unsupported company')
    key = 'quote:'+symbol
    if store.rpc('radar_claim_data', {'p_key': key, 'p_seconds': 30}):
        try:
            data = provider_get('/v2/stocks/quotes/latest', {'symbols': symbol, 'feed': 'iex'})
            payload = quote_payload(symbol, data)
            store.request('radar_data_cache', query='id=eq.'+key, rows={'payload': payload, 'last_error': None}, method='PATCH')
        except (MarketError, ValueError, KeyError, TypeError):
            store.request('radar_data_cache', query='id=eq.'+key, rows={'last_error': 'Live quote unavailable or invalid'}, method='PATCH')
    rows = store.request('radar_data_cache', query='select=payload,last_error&id=eq.'+key+'&limit=1')
    row = rows[0] if rows else {}; payload = dict(row.get('payload') or {})
    if not payload: return {'status': 'unavailable', 'entry_eligible': False, 'reason': row.get('last_error') or 'No verified quote received'}
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(payload['observed_at'])).total_seconds()
    payload.update(age_seconds=max(0, age), status='fresh_quote' if age <= POLICY['stock_quote_max_age_seconds'] else 'stale', last_error=row.get('last_error'))
    return payload


def capabilities(store):
    configured = bool(os.getenv('ALPACA_API_KEY') and os.getenv('ALPACA_API_SECRET'))
    caches = store.request('radar_market_cache', query='select=symbol,updated_at,last_error&limit=40')
    return {'prices': {'credentials_configured': configured, 'public_use_confirmed': enabled(),
        'cadence': 'bounded on-demand polling; daily scheduled research', 'feed': 'IEX only',
        'cached_company_count': len(caches), 'last_error_count': sum(bool(r.get('last_error')) for r in caches)},
        'options': {'public_use_confirmed': os.getenv('RADAR_OPTIONS_DISPLAY_AUTHORIZED','false').lower()=='true',
            'feed': os.getenv('RADAR_OPTIONS_FEED','indicative'), 'executable_feed_required': 'OPRA'},
        'assistant': {'mode': 'bounded structured evidence workflow',
            'generative_enabled': os.getenv('RADAR_AI_ENABLED','false').lower()=='true' and bool(os.getenv('GROQ_API_KEY'))},
        'forecasts': {'enabled': False, 'reason': 'No model has passed point-in-time validation'},
        'execution_enabled': False, 'paid_services_enabled': False}
