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
    return fetch_all(conn,'''SELECT a.*,e.title,e.provider,e.published_at,e.first_seen_at,e.backfill,e.tickers,e.provenance,e.metadata AS source_metadata,n.payload AS analysis_payload FROM alerts a JOIN evidence e ON e.id=a.evidence_id JOIN analyses n ON n.id=a.analysis_id ORDER BY a.updated_at DESC LIMIT ?''',(limit,))

def card(row):
    a=json.loads(row['analysis_payload']);p=json.loads(row['payload'])
    tickers=json.loads(row['tickers']); label=' · '.join(tickers) or 'MARKET WATCH'
    mode='Historical / backfill' if row['backfill'] else 'New event'
    strength='Primary source' if row['provenance']=='primary' else 'Secondary report'
    age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(row['published_at'])).total_seconds()/3600)
    metadata=json.loads(row['source_metadata'])
    publication=local_time(row['published_at'])
    if metadata.get('publication_precision')=='filing_date_end_of_day_bound':
        publication=metadata['filed']+' · filing date only (no intraday timestamp)'
    h=html.escape
    st.markdown(f'''<div class="radar-card">
    <div class="radar-kicker">{h(label)}</div>
    <h3>{h(row['title'])}</h3>
    <span class="radar-badge">{h(a['suggested_action'].upper())}</span>
    <span class="radar-badge">{h(strength)}</span>
    <div class="radar-muted">{h(row['provider'])} · {h(publication)} · {age:.1f}h old · {h(mode)}</div>
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
    c2.metric('Feeds with evidence',len(health['coverage']))
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
                with get_conn(path) as conn:
                    docs=fetch_all(conn,"SELECT id,metadata FROM evidence WHERE provider='sec_document' AND json_extract(metadata,'$.parent_evidence_id')=? ORDER BY revision DESC LIMIT 1",(row['evidence_id'],))
                if docs:
                    metadata=json.loads(docs[0]['metadata'])
                    st.caption('Primary filing excerpts — issuer statements, not independent confirmation. Offsets refer to normalized filing text.')
                    for snippet in metadata.get('excerpts',[])[:3]:
                        st.text(snippet['text'])
                        st.caption(f"Evidence #{docs[0]['id']} · characters {snippet['start']}–{snippet['end']}")
                st.write('Bull case:', '; '.join(a['bullish_implications']) or 'Not established')
                st.write('Bear case:', '; '.join(a['bearish_implications']) or 'Not established')
                st.write('Counterevidence:', '; '.join(a['counterevidence']) or 'Not yet collected')
                st.write('Invalidation:', '; '.join(a['invalidation_conditions']))
                st.write('Missing:', '; '.join(a['missing_information']))
                st.caption(f"Alert #{row['id']} · revision {row['revision']} · policy status: {a['policy_status']}")
            if st.button('Evaluate & log',key=f"evaluate_{row['id']}"):
                from earnings_radar.evaluation import evaluate_research_event,record
                with get_conn() as conn:
                    schedules=fetch_all(conn,'SELECT * FROM earnings_events WHERE superseded_by IS NULL')
                    quotes=fetch_all(conn,'SELECT * FROM option_quotes')
                with get_conn(path) as conn:
                    evidence=dict(conn.execute('SELECT * FROM evidence WHERE id=?',(row['evidence_id'],)).fetchone())
                    result=evaluate_research_event(evidence,schedules,quotes)
                    result['analysis_id']=row['analysis_id']
                    result['alert_revision']=row['revision']
                    evaluation_id=record(conn,result,alert_id=row['id'],evidence_id=row['evidence_id'])
                st.info(f"Evaluation #{evaluation_id}: {result['action'].upper()} — {', '.join(result['reasons']) or 'eligible conservative paper package'}")
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
        if source['id']=='sec_fundamentals':
            fundamental_jobs=[j for j in health['jobs'] if j['name'].startswith('sec_fundamentals:')]
            source['runtime_status']='healthy' if fundamental_jobs and all(j['status']=='healthy' for j in fundamental_jobs) else 'degraded_or_not_started'
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

def opportunities():
    theme()
    st.header('Opportunities · your research shortlist')
    st.caption('Compare a defined-risk paper package only when verified live data exists. Ask-based cost is not an expected earnings move.')
    from earnings_radar.evaluation import evaluate,record
    from earnings_radar.paper import SUPPORTED
    from earnings_radar.opportunity import exposures
    with get_conn() as conn:
        events=fetch_all(conn,'SELECT * FROM earnings_events WHERE superseded_by IS NULL ORDER BY earnings_date')
        quotes=fetch_all(conn,'SELECT * FROM option_quotes')
    if not events:st.info('No confirmed earnings events available. Import a primary-source schedule under Import; SEC filing collection is not a future earnings calendar.');return
    labels={e['id']:f"{e['ticker']} · {e['earnings_date']} {e['earnings_time']}" for e in events}
    eid=st.selectbox('Earnings event',list(labels),format_func=lambda k:labels[k])
    event=next(e for e in events if e['id']==eid)
    c1,c2,c3=st.columns(3)
    strategy=c1.selectbox('Package',list(SUPPORTED))
    fees=c2.number_input('Total simulated fees ($)',min_value=0.0,value=2.0)
    slippage=c3.number_input('Slippage per share ($)',min_value=0.0,value=.05)
    quantity=st.number_input('Paper quantity',min_value=1,value=1)
    result=evaluate(event,quotes,strategy=strategy,quantity=quantity,fees=fees,slippage=slippage)
    if not result['eligible']:
        st.warning('WAIT · No eligible option package')
        st.write('Needs:',', '.join(result['reasons']))
        st.caption('Historical, indicative, delayed and sample quotes cannot support a live trade suggestion. No live options adapter has been verified yet.')
    else:
        cols=st.columns(3);cols[0].metric('Simulated entry cost',f"${result['cost']:,.2f}");cols[1].metric('Maximum loss',f"${result['maximum_loss']:,.2f}");cols[2].metric('Quote age',f"{result['quote_age_seconds']:.0f}s")
        st.write('Expiration breakevens:',result['expiration_breakevens'])
        st.dataframe(pd.DataFrame(result['expiration_scenarios']),width='stretch',hide_index=True)
        st.caption('These are expiration payoff scenarios, not intraday valuation or forecasts. Quote sizes and fills remain unverified.')
    save_trade=st.checkbox('Also add an eligible evaluation to the paper journal',value=False,disabled=not result['eligible'])
    if st.button('Record paper evaluation'):
        with get_conn() as conn:
            evaluation_id=record(conn,result)
            if save_trade and result['eligible']:
                from earnings_radar.evaluation import journal_candidate
                journal_candidate(conn,evaluation_id,thesis='Evidence review pending; conservative paper simulation',invalidation='Source correction or loss of quote eligibility')
        st.success(f'Saved immutable evaluation #{evaluation_id}; simulated outcomes only.')
    with get_conn(prepare()) as conn:related=exposures(conn,event['ticker'],datetime.now(timezone.utc))
    st.subheader('Reported fundamentals')
    from earnings_radar.earnings_analysis import summarize
    with get_conn(prepare()) as conn:fundamentals=summarize(conn,event['ticker'],datetime.now(timezone.utc))
    if fundamentals:st.dataframe(pd.DataFrame(fundamentals),width='stretch',hide_index=True)
    else:st.info('No reported fundamentals collected for this ticker yet.')
    st.subheader('Related-company research')
    if related:st.dataframe(pd.DataFrame(related),width='stretch')
    else:st.info('No documented, dated company relationships collected. Supplier or peer picks will not be invented.')

def systemic_page():
    st.header('Systemic risk · market-wide watch')
    from earnings_radar.systemic import assess
    status=assess({},datetime.now(timezone.utc))
    st.warning('UNKNOWN · independent indicator coverage is incomplete')
    st.caption('Policy headlines provide context. They do not substitute for volatility, credit spreads, breadth, banking and funding indicators. No crash probability is estimated.')
    rows=[{'Dimension':k.replace('_',' ').title(),**v} for k,v in status['dimensions'].items()]
    st.dataframe(pd.DataFrame(rows),width='stretch',hide_index=True)
    st.write(status['conclusion'])
    with get_conn(prepare()) as conn:rows=board_rows(conn)
    for row in rows:
        if json.loads(row['analysis_payload'])['category']=='systemic':card(row)

def earnings(calendar_page):
    st.header('Earnings · results and calendar')
    results,calendar=st.tabs(['Reported financial results','Upcoming schedule'])
    with results:
        from earnings_radar.earnings_analysis import summarize
        with get_conn(prepare()) as conn:
            rows=fetch_all(conn,"SELECT tickers FROM evidence WHERE provider='sec_fundamentals'")
        tickers=sorted({t for row in rows for t in json.loads(row['tickers'])})
        if not tickers:st.info('Start the SEC worker to collect reported revenue, net income and gross profit. No earnings estimates are fabricated.')
        else:
            ticker=st.selectbox('Company',tickers)
            with get_conn(prepare()) as conn:metrics=summarize(conn,ticker,datetime.now(timezone.utc))
            st.dataframe(pd.DataFrame(metrics),width='stretch',hide_index=True)
            st.caption('USD values are reported historical financial facts. Period lengths and comparison evidence are explicit. Consensus, future guidance and current prices remain unknown.')
    with calendar:
        st.info('SEC filings establish past reported facts, not upcoming announcement dates. A verified calendar feed is still required; manual primary-source imports remain available.')
        calendar_page()
