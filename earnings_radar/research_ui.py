"""Scan-friendly research board and persistent inbox. Collection stays in the worker."""
import html
import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from earnings_radar.db import get_conn,fetch_all,utc_now
from earnings_radar.sources import prepare,research_path
from earnings_radar.health import snapshot
from earnings_radar.settings import Settings

NY=ZoneInfo('America/New_York')

def theme():
    st.markdown('''<style>
    .stApp { background:#0b1220; color:#e9eef7; }
    [data-testid="stSidebar"] {background:#101b2e;}
    h1,h2,h3 {letter-spacing:-0.035em;}
    .radar-hero {background:linear-gradient(115deg,#153252,#11233a);border:1px solid #2d4e70;border-radius:18px;padding:26px;margin-bottom:20px;}
    .radar-kicker {color:#74e7bb;font-weight:800;font-size:12px;letter-spacing:.15em;text-transform:uppercase;}
    .radar-hero h1 {font-size:38px;margin:5px 0; color:#fff;}
    .radar-card {border:1px solid #2c405c;border-radius:14px;background:#122038;padding:20px;min-height:290px;margin:8px 0 18px;}
    .radar-card h3 {color:#fff;font-size:23px;line-height:1.25;margin:12px 0;}
    .radar-badge {border-radius:6px;padding:5px 9px;background:#164738;color:#8af0c3;font-weight:800;font-size:12px;display:inline-block;margin:0 5px 5px 0;}
    .radar-muted {font-size:13px;color:#a9b9cf;}
    .radar-label {font-weight:750;color:#d5e2f4;font-size:13px;margin-top:12px;}
    .radar-risk {background:#322b20;color:#f4d69c;border-radius:8px;padding:9px;font-size:13px;margin-top:14px;}
    </style>''',unsafe_allow_html=True)

def local_time(value):
    return datetime.fromisoformat(value).astimezone(NY).strftime('%b %d, %I:%M %p ET')

def board_rows(conn,limit=24):
    return fetch_all(conn,'''SELECT a.*,e.title,e.provider,e.published_at,e.first_seen_at,e.backfill,e.tickers,e.provenance,n.payload AS analysis_payload FROM alerts a JOIN evidence e ON e.id=a.evidence_id JOIN analyses n ON n.id=a.analysis_id ORDER BY a.updated_at DESC LIMIT ?''',(limit,))

def card(row):
    a=json.loads(row['analysis_payload']);p=json.loads(row['payload'])
    tickers=json.loads(row['tickers']); label=' · '.join(tickers) or 'MARKET WATCH'
    mode='Historical / backfill' if row['backfill'] else 'New event'
    strength='Primary source' if row['provenance']=='primary' else 'Secondary report'
    age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(row['published_at'])).total_seconds()/3600)
    h=html.escape
    st.markdown(f'''<div class="radar-card">
    <div class="radar-kicker">{h(label)}</div>
    <h3>{h(row['title'])}</h3>
    <span class="radar-badge">{h(a['suggested_action'].upper())}</span>
    <span class="radar-badge">{h(strength)}</span>
    <div class="radar-muted">{h(row['provider'])} · {h(local_time(row['published_at']))} · {age:.1f}h old · {h(mode)}</div>
    <div class="radar-label">THE SIGNAL</div><div>{h(a['economic_mechanism'])}</div>
    <div class="radar-label">EVIDENCE STRENGTH</div><div>{h(a['evidence_confidence'].title())} for source attribution · trade outcome unknown</div>
    <div class="radar-risk">Quote check: {h(p['feed_type'])}. Wait for full-document review and a valid evaluation before considering a trade.</div>
    </div>''',unsafe_allow_html=True)

def today():
    theme()
    st.markdown('''<div class="radar-hero"><div class="radar-kicker">EARNINGS RADAR · RESEARCH DESK</div><h1>Your weekly picks board</h1><p>What changed. What to watch. What would change the thesis.</p></div>''',unsafe_allow_html=True)
    path=prepare()
    with get_conn(path) as conn:
        health=snapshot(conn);rows=board_rows(conn)
    c1,c2,c3=st.columns(3)
    c1.metric('Worker',health['worker'].replace('_',' ').title())
    c2.metric('Sources with evidence',len(health['coverage']))
    c3.metric('Research alerts',len(rows))
    st.caption('Picks are a research shortlist, not betting odds or promises of returns. Source evidence and trade eligibility are separate.')
    if health['worker']!='running':st.warning('Background collection is stopped or unknown. Start the worker from Connections; this screen does not run collection.')
    choice=st.radio('Board', ['This week','All recent research','Unread'],horizontal=True)
    now=datetime.now(NY);week=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    if choice=='This week':rows=[r for r in rows if datetime.fromisoformat(r['first_seen_at'])>=week]
    if choice=='Unread':rows=[r for r in rows if not r['read_at']]
    if not rows:st.info('No research alerts for this view. Configure approved sources and start the worker. No sample picks appear in research mode.');return
    columns=st.columns(2)
    for i,row in enumerate(rows):
        with columns[i%2]:
            card(row)
            with st.expander('Evidence, bull/bear case & invalidation'):
                a=json.loads(row['analysis_payload']);p=json.loads(row['payload'])
                st.link_button('Open source',p['primary_evidence']['url'])
                st.write('Bull case:', '; '.join(a['bullish_implications']) or 'Not established')
                st.write('Bear case:', '; '.join(a['bearish_implications']) or 'Not established')
                st.write('Counterevidence:', '; '.join(a['counterevidence']) or 'Not yet collected')
                st.write('Invalidation:', '; '.join(a['invalidation_conditions']))
                st.write('Missing:', '; '.join(a['missing_information']))
                st.caption(f"Alert #{row['id']} · revision {row['revision']} · policy status: {a['policy_status']}")
            if st.button('Mark reviewed',key=f"review_{row['id']}"):
                with get_conn(path) as conn:conn.execute('UPDATE alerts SET read_at=? WHERE id=?',(utc_now(),row['id']))
                st.rerun()

def evidence_page():
    st.header('Evidence library')
    st.caption('Immutable source revisions, attribution and measured arrival delay. Titles are source reports, not independently verified full-document conclusions.')
    with get_conn(prepare()) as conn:
        rows=fetch_all(conn,'SELECT id,provider,provider_event_id,revision,title,url,published_at,first_seen_at,retrieved_at,tickers,provenance,claim_type,backfill FROM evidence ORDER BY id DESC LIMIT 200')
    if rows:st.dataframe(pd.DataFrame(rows),width='stretch',hide_index=True)
    else:st.info('No real evidence collected yet. See Connections for setup.')

def connections():
    st.header('Connections & coverage')
    path=prepare();settings=Settings()
    with get_conn(path) as conn:
        health=snapshot(conn);sources=fetch_all(conn,'SELECT * FROM source_registry ORDER BY category,name')
    st.write('Research database:',str(path))
    st.write('Worker:',health['worker'])
    st.code('python -m earnings_radar.worker\nstreamlit run app.py',language='bash')
    st.caption('Run these from the repository with .venv activated. The worker keeps collecting when the browser closes. A sleeping machine cannot monitor continuously.')
    st.subheader('Source directory')
    statuses={j['name']:j for j in health['jobs']}
    sec=[j for j in health['jobs'] if j['name'].startswith('sec:')]
    for source in sources:
        source['runtime_status']=statuses.get(source['id'],{}).get('status','not_connected')
        if source['id']=='sec':source['runtime_status']='healthy' if sec and all(j['status']=='healthy' for j in sec) else 'degraded_or_not_started'
    st.dataframe(pd.DataFrame(sources),width='stretch',hide_index=True)
    st.subheader('Collection health')
    if health['jobs']:st.dataframe(pd.DataFrame(health['jobs']),width='stretch',hide_index=True)
    else:st.info('Worker has not started. It seeds durable collection jobs on first run.')
    st.write('Analysis backlog:',health['analysis_backlog'])
    st.write('Model budget reserved today ($):',health['model_reserved_usd_today'])
    st.caption('Budget reservation is not a billing receipt. Source publication delay and internal processing delay are different measurements.')
    if health['delays']:st.json(health['delays'])
    requirements={'SEC request contact':bool(settings.sec_user_agent),'Alpaca credentials':settings.alpaca_available,'Model enabled':settings.model_enabled,'Notifications enabled':settings.telegram_enabled,'Notification destination verified':settings.telegram_verified}
    st.write(requirements)
    st.info('Licensed outlets need authorized feeds or APIs. Yahoo/Google/EarningsHub/Truth access is not verified. Add credentials securely; never paste them into research notes. See docs/PROVIDERS.md and docs/RUNBOOK.md.')
