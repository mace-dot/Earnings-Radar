"""Supported long-option legs and expiration payoff, including costs and fees."""
from earnings_radar.validation import number, iso_date

SUPPORTED = {'long_call': ('call',), 'long_put': ('put',), 'long_straddle': ('call','put')}

def validate_legs(legs):
    if not legs:
        raise ValueError('at least one leg required')
    for leg in legs:
        if leg['side'] != 'buy' or leg['option_type'] not in {'call','put'}:
            raise ValueError('only long calls and puts supported')
        iso_date(leg['expiration'])
        for k in ('strike','quantity','multiplier'):
            if number(leg[k], integer=k != 'strike', positive=True) is None:
                raise ValueError(k+' required')
        if number(leg['premium']) is None:
            raise ValueError('premium required')
    return legs

def cost(legs, fees=0):
    validate_legs(legs)
    return round(sum(l['premium']*l['multiplier']*l['quantity'] for l in legs)+number(fees), 2)

def expiration_pnl(legs, spot, fees=0):
    validate_legs(legs)
    spot = number(spot)
    if spot is None:
        raise ValueError('spot required')
    value = sum(max(0, spot-l['strike'] if l['option_type']=='call' else l['strike']-spot)*l['multiplier']*l['quantity'] for l in legs)
    return round(value-cost(legs, fees), 2)

def from_manual(trade):
    strategy = trade['strategy']
    if strategy not in SUPPORTED:
        raise ValueError('strategy has no supported leg representation')
    legs = [dict(side='buy',quantity=trade.get('contracts',1),strike=trade['strike'],expiration=trade['expiration'],option_type=kind,multiplier=trade.get('multiplier',100),contract_id=trade.get(kind+'_contract_id'),premium=trade.get('entry_'+kind+'_ask')) for kind in SUPPORTED[strategy]]
    return validate_legs(legs)
