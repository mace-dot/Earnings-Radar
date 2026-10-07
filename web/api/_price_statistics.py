"""Descriptive daily-bar statistics. No forecast probability or trade instruction."""
import math
import statistics
from datetime import datetime, timezone


def summarize(bars, benchmark=()):
    if len(bars) < 61:
        return {'status': 'insufficient_history', 'required_bars': 61, 'available_bars': len(bars)}
    dates = []; closes = []; ranges = []
    for b in bars:
        stamp = datetime.fromisoformat(b['t'].replace('Z', '+00:00'))
        if stamp.tzinfo is None: raise ValueError('Bar timestamp requires timezone')
        day = stamp.astimezone(timezone.utc).date().isoformat()
        if dates and day <= dates[-1]: raise ValueError('Bars must have unique ascending session dates')
        c, h, low = float(b['c']), float(b['h']), float(b['l'])
        if not all(math.isfinite(v) and v > 0 for v in (c,h,low)) or not low <= c <= h:
            raise ValueError('Invalid OHLC bar')
        ranges.append(max(h-low, abs(h-closes[-1]), abs(low-closes[-1])) if closes else h-low)
        dates.append(day); closes.append(c)
    r = [math.log(b/a) for a,b in zip(closes, closes[1:])]
    sigma20 = statistics.stdev(r[-20:]); sigma60 = statistics.stdev(r[-60:])
    baseline = r[-61:-1]
    baseline_sigma = statistics.stdev(baseline)
    z = (r[-1] - statistics.mean(baseline))/baseline_sigma if baseline_sigma else None
    beta = None; relative = None
    if benchmark:
        # Validate benchmark independently, without recursively comparing to another series.
        check = summarize(benchmark)
        if check['status'] == 'available':
            br = {datetime.fromisoformat(b['t'].replace('Z','+00:00')).astimezone(timezone.utc).date().isoformat(): math.log(float(b['c'])/float(a['c'])) for a,b in zip(benchmark, benchmark[1:])}
            pairs = [(r[i-1], br[d]) for i,d in enumerate(dates) if i and d in br][-60:]
            if len(pairs) >= 40:
                x,y = zip(*pairs); variance = statistics.variance(y)
                beta = statistics.covariance(x,y)/variance if variance else None
            if dates[-1] in br: relative = r[-1] - br[dates[-1]]
    ratio = sigma20 / sigma60 if sigma60 else None
    flags = []
    if ratio is not None and ratio < .7: flags.append('Volatility compression: recent daily variation is below its 60-session baseline; direction and timing are unknown.')
    if z is not None and abs(z) >= 2: flags.append('Unusual latest daily move relative to prior sessions; investigate source evidence and market context.')
    return {'status': 'available', 'as_of_session': dates[-1], 'bars': len(bars),
            'realized_volatility_20': sigma20 * math.sqrt(252), 'realized_volatility_60': sigma60 * math.sqrt(252),
            'volatility_ratio': ratio, 'latest_return_zscore': z, 'atr_14': statistics.mean(ranges[-14:]),
            'atr_percent_14': statistics.mean(ranges[-14:])/closes[-1], 'momentum_20': closes[-1]/closes[-21]-1,
            'drawdown_60': closes[-1]/max(closes[-60:])-1, 'beta_60': beta,
            'benchmark_relative_log_return': relative, 'flags': flags,
            'interpretation': 'Historical statistics, not a prediction. A difference from market consensus is unverified without documented expectations and comparable primary results.',
            'missing': ['Verified consensus expectations', 'Executable options prices and implied volatility', 'Upcoming earnings confirmation', 'Out-of-sample predictive validation']}

# Enrich the original descriptive measures without introducing forecast probabilities.
_basic_summary=summarize
def summarize(bars,benchmark=()):
 result=_basic_summary(bars,benchmark)
 if result['status']!='available':return result
 close=[float(b['c']) for b in bars];returns=[math.log(b/a) for a,b in zip(close,close[1:])]
 volume=[float(b.get('v',0)) for b in bars];base=statistics.mean(volume[-21:-1])
 result.update({'latest_close':close[-1],'daily_return':close[-1]/close[-2]-1,'momentum_60':close[-1]/close[-61]-1,
  'volume_ratio_20':volume[-1]/base if base>0 else None,
  'volume_note':'Compare within the same feed; this is not necessarily consolidated volume.',
  'parkinson_volatility_20':math.sqrt(252*statistics.mean([math.log(float(b['h'])/float(b['l']))**2 for b in bars[-20:]])/(4*math.log(2))),
  'mean_daily_log_return_60':statistics.mean(returns[-60:]),'sample_size':len(returns),
  'methods':'Log-return standard deviation × √252; true-range ATR; latest move z-score; Parkinson high/low estimate. Descriptive statistics, not forecast probabilities.'})
 return result
