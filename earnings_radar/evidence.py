"""Evidence classification without treating a headline as an enacted policy."""
import re

def classify(evidence):
    title=evidence['title'].lower()
    political=any(w in title for w in ('trump','tariff','executive order','sanction'))
    if political:
        # Primary signed documents require separately reviewed implementation evidence.
        status='unknown'
        for word,label in [('revers','reversal'),('amend','amendment'),('propos','proposal'),('threat','threat'),('said','statement'),('says','statement'),('signed','reported_signed_action')]:
            if word in title: status=label;break
        if evidence['provenance']!='primary' and status=='reported_signed_action':status='unknown'
        return 'political',status
    if any(w in title for w in ('earnings','10-q','10-k','guidance','8-k')):return 'earnings','not_applicable'
    if evidence['provider'].startswith('fed_') or any(w in title for w in ('credit','funding','volatility','banking')):return 'systemic','not_applicable'
    return 'general','not_applicable'
