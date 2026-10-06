import math
from datetime import datetime, timezone, timedelta
import pytest
from earnings_radar.quantitative import summarize

def bars(returns):
    price=100; result=[]
    for i, r in enumerate([0,*returns]):
        price *= math.exp(r)
        result.append({'t':(datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(days=i)).isoformat(), 'c':price, 'h':price*1.01, 'l':price*.99})
    return result

def test_sample_vol_and_beta_are_known():
    series=bars([.01,-.01]*40)
    q=summarize(series, series)
    assert q['realized_volatility_20']==pytest.approx(.01*math.sqrt(20/19)*math.sqrt(252))
    assert q['beta_60']==pytest.approx(1)
    assert q['benchmark_relative_log_return']==pytest.approx(0)
    assert q['momentum_20']==pytest.approx(0)
    assert q['atr_percent_14'] > 0

def test_no_undefined_zero_variance_scores():
    q=summarize(bars([0]*70))
    assert q['latest_return_zscore'] is None
    assert q['volatility_ratio'] is None
    assert q['flags']==[]

def test_history_and_bad_data():
    assert summarize(bars([.01]*10))['status']=='insufficient_history'
    series=bars([.01]*70); series[-1]['c']=float('nan')
    with pytest.raises(ValueError): summarize(series)
    series=bars([.01]*70); series[-1]['t']=series[-2]['t']
    with pytest.raises(ValueError): summarize(series)

def test_latest_move_excluded_from_zscore_baseline():
    q=summarize(bars([.001,-.001]*40+[.05]))
    assert q['latest_return_zscore']>40
    assert any('Unusual' in f for f in q['flags'])
