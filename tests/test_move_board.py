from datetime import datetime,timezone
from web.api._board import company_board

def events():
 return [{'id':'a'*64,'symbol':'AAPL','title':'Apple result','provider':'sec_fundamentals','tickers':['AAPL'],'published_at':'2026-10-05T00:00:00+00:00','retrieved_at':'2026-10-06T00:00:00+00:00','evidence_meta':{'tag':'NetIncomeLoss','end':'2026-09-30'},'research':{'takeaway':'Profit improved','calculations':[{'label':'Year-over-year change','value':20}],'ranking':{'score':45}}}]
NOW=datetime(2026,10,6,tzinfo=timezone.utc)

def test_growth_never_infers_price_direction_or_ready_option():
 b=company_board(events(),{}, {},NOW)[0]
 assert b['name']=='Apple' and b['business_signal']=='Business growing'
 assert b['direction']=='Not confirmed'
 assert b['movement']=='Price data needed'
 assert b['hidden_edge'].startswith('Unverified')
 assert b['stress_status']=='Crisis risk not established'

def test_old_market_data_does_not_create_current_volatility_signal():
 state={'quantitative':{'AAPL':{'status':'available','as_of_session':'2026-01-01','latest_return_zscore':10}}}
 assert company_board(events(),{},state,NOW)[0]['movement']=='Old price data'

def test_funding_flag_retains_period_and_evidence():
 ratios={'AAPL':[{'label':'Interest coverage','value':.5,'period_end':'2026-06-30','evidence_ids':['x','y']}]}
 b=company_board(events(),ratios,{},NOW)[0]
 assert len(b['stress_flags'])==1 and b['stress_flags'][0]['evidence_ids']==['x','y']
 assert b['stress_status']=='Funding questions to investigate'
 assert b['direction']=='Not confirmed'

def test_zero_variance_and_nonfinite_quant_values_do_not_trigger_flags():
 state={'quantitative':{'AAPL':{'status':'available','as_of_session':'2026-10-05','volatility_ratio':float('nan'),'latest_return_zscore':None}}}
 assert company_board(events(),{},state,NOW)[0]['movement']=='Usual recent movement'
