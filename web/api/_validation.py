"""Offline chronological probability evaluation. Reports never promote models."""
import math
from datetime import datetime,timezone


def stamp(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if not t.tzinfo:raise ValueError('Evaluation timestamps require timezone')
    return t


def metrics(rows,baseline):
    if not rows:raise ValueError('No evaluation observations')
    bins=[]
    for i in range(10):
        group=[r for r in rows if min(9,int(r['probability']*10))==i]
        if group:bins.append({'bin':i,'count':len(group),
            'mean_prediction':sum(r['probability'] for r in group)/len(group),
            'observed_frequency':sum(r['outcome'] for r in group)/len(group)})
    epsilon=1e-12
    def loss(p,y):
        p=min(1-epsilon,max(epsilon,p));return -(y*math.log(p)+(1-y)*math.log1p(-p))
    return {'count':len(rows),'brier':sum((r['probability']-r['outcome'])**2 for r in rows)/len(rows),
        'baseline_brier':sum((baseline-r['outcome'])**2 for r in rows)/len(rows),
        'log_loss':sum(loss(r['probability'],r['outcome']) for r in rows)/len(rows),
        'baseline_log_loss':sum(loss(baseline,r['outcome']) for r in rows)/len(rows),
        'calibration_bins':bins}


def walk_forward(observations,min_train=30,test_size=10):
    if min_train<2 or test_size<2:raise ValueError('Invalid evaluation partition size')
    rows=[];seen=set();scope=None
    for r in observations:
        required={'id','issued_at','outcome_at','probability','outcome','universe','target','horizon_sessions','feature_cutoff'}
        if not required<=r.keys():raise ValueError('Missing point-in-time evaluation fields')
        if r['id'] in seen:raise ValueError('Duplicate observations')
        seen.add(r['id']);p=r['probability'];y=r['outcome']
        if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<=p<=1 or type(y) is not int or y not in (0,1):raise ValueError('Invalid probability or outcome')
        issued=stamp(r['issued_at']);outcome=stamp(r['outcome_at']);cutoff=stamp(r['feature_cutoff'])
        if outcome>datetime.now(timezone.utc):raise ValueError('Outcome has not yet occurred')
        if cutoff>issued or outcome<=issued:raise ValueError('Future-feature leakage or invalid outcome time')
        current=(r['universe'],r['target'],r['horizon_sessions'])
        if scope is not None and scope!=current:raise ValueError('Mixed target/universe/horizon')
        scope=current;rows.append({**r,'_issued':issued,'_outcome':outcome})
    rows.sort(key=lambda r:r['_issued'])
    folds=[]
    for start in range(min_train,len(rows)-test_size+1,test_size):
        test=rows[start:start+test_size];boundary=test[0]['_issued']
        # Outcomes unavailable at the fold cutoff cannot become training information.
        train=[r for r in rows[:start] if r['_outcome']<boundary]
        groups={r.get('event_group') for r in test if r.get('event_group')}
        train=[r for r in train if not r.get('event_group') or r['event_group'] not in groups]
        if len(train)<min_train:continue
        baseline=(sum(r['outcome'] for r in train)+1)/(len(train)+2)
        folds.append({'test_start':test[0]['issued_at'],'test_end':test[-1]['issued_at'],
            'training_count':len(train),'test_ids':[r['id'] for r in test],**metrics(test,baseline)})
    return {'status':'review_required' if folds else 'insufficient_history','folds':folds,
        'universe_target_horizon':scope,'model_promoted':False,'live_forecasts_enabled':False,
        'limitations':['Partition sizes are engineering defaults, not a universal sample-size justification.',
            'This report cannot prove economic profitability or validate option fills.',
            'Independent review, untouched testing, sample uncertainty and cost evaluation remain required.']}
