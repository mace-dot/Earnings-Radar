"""The user's proposed decision contract; execution/probabilities remain disabled."""
import json
from pathlib import Path
CONTRACT=json.loads(Path(__file__).with_name('research_policy.json').read_text())
if CONTRACT['scope']['broker_execution'] or CONTRACT['scope']['paid_services_enabled']:
    raise ValueError('This deployment does not support execution or paid-service activation')
DEFAULTS=CONTRACT['proposed_defaults']
POLICY_VERSION='research-policy-1'
POLICY={
    'version':POLICY_VERSION,'schema_version':CONTRACT['schema_version'],
    'validated':False,'execution_enabled':False,
    'stock_quote_max_age_seconds':DEFAULTS['stock_quote_max_age_seconds_open_session'],
    'option_quote_max_age_seconds':DEFAULTS['option_quote_max_age_seconds_open_session'],
    'spread_fraction_review':DEFAULTS['option_spread_review_if_fraction_of_mid_exceeds'],
    'spread_dollars_review':DEFAULTS['option_spread_review_if_absolute_dollars_exceeds'],
    'delta_range':DEFAULTS['delta_comparison_range'],'expiry_days_range':DEFAULTS['days_to_expiry_comparison_range'],
    'probabilities_enabled':False,'personal_sizing_enabled':False,
    'meaning':'Proposed research defaults awaiting out-of-sample validation; not manager entry rules.'}
