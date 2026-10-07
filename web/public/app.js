'use strict';
let data = {events: [], status: [], weekly: [], financial_context: {}, source_health: []};
let view = 'brief', user = null, watchlist = [], selected = null;
const $ = s => document.querySelector(s);
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined) n.textContent=text; if(cls)n.className=cls; return n; };
const date = s => { const d=new Date(s); return Number.isNaN(d.valueOf())?'Unavailable':d.toLocaleString(); };
const pct = v => typeof v==='number'&&Number.isFinite(v)?`${v.toFixed(1)}%`:'Unavailable';
function sourceLink(url,label){
 const n=el('a',label);try{const u=new URL(url);if(u.protocol!=='https:'||u.username||u.password)return el('span',label);n.href=u.href;}catch{return el('span',label);}
 n.target='_blank';n.rel='noopener noreferrer';return n;
}
function list(root,title,values){root.append(el('h3',title,'label'));if(!values?.length){root.append(el('p','Not established from collected evidence.'));return;}const ul=el('ul');for(const v of values)ul.append(el('li',v));root.append(ul);}
async function api(path,payload){
 const r=await fetch(path,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const d=await r.json();if(!r.ok)throw new Error(d.error||'Request failed');return d;
}
function heading(title,text){$('#view-heading').replaceChildren(el('h2',title),el('p',text));}
function latest(records){
 const keys=new Set();return [...records].sort((a,b)=>(b.evidence_meta?.end||b.published_at).localeCompare(a.evidence_meta?.end||a.published_at)||b.retrieved_at.localeCompare(a.retrieved_at)).filter(e=>{const m=e.evidence_meta||{};const annual=m.start&&(new Date(m.end)-new Date(m.start))/86400000>=350;const key=e.provider==='sec_fundamentals'?`${e.tickers.join(',')}:${m.tag||e.provider_event_id}:${annual?'annual':'quarter_or_balance'}`:e.story_key||`${e.provider}:${e.provider_event_id}`;if(keys.has(key))return false;keys.add(key);return true;}).sort((a,b)=>(b.research?.ranking?.score||0)-(a.research?.ranking?.score||0));
}
function card(e){
 const r=e.research||{},n=el('article',undefined,'card'),top=el('div',undefined,'top');
 top.append(el('span',e.institution||e.provider),el('span',r.action||'Investigate','badge'));n.append(top);
 const symbols=el('div',undefined,'symbols');for(const s of e.tickers||[]){const b=el('button',s);b.addEventListener('click',()=>showCompany(s));symbols.append(b);}if(!e.tickers?.length)symbols.append(el('span','MACRO / POLICY'));n.append(symbols);
 n.append(el('h2',r.takeaway||e.title),el('h3','Why it matters','label'),el('p',r.mechanism||'Interpretation is not available.'));
 n.append(el('div',`Next step: ${r.next_step||'Read the primary source.'}`,'next-step'));
 const rank=r.ranking||{};n.append(el('p',`Research priority ${rank.score??'—'} · Published ${date(e.published_at)}`));
 n.append(sourceLink(e.url,'Open supporting source ↗'));
 const detail=el('details');detail.append(el('summary','Bull / bear case, calculations & evidence'));
 list(detail,'Bull case — conditional',r.bull);list(detail,'Bear case — conditional',r.bear);list(detail,'Counterevidence & uncertainty',r.counterevidence);
 detail.append(el('h3','Expectations versus reality','label'),el('p',r.expectations||'Unverified'),el('p',`Catalyst: ${r.catalyst||'Not confirmed'}`),el('p',`Horizon: ${r.horizon||'Unspecified'}`));
 for(const c of r.calculations||[]){detail.append(el('p',`${c.label}: ${typeof c.value==='number'?c.value.toFixed(2):'Unavailable'} ${c.unit||''}. ${c.explanation||''}`));for(const id of c.evidence_ids||[]){const source=data.events.find(x=>x.id===id);if(source)detail.append(sourceLink(source.url,`Calculation source: ${source.title}`));}}
 list(detail,'What would invalidate the thesis',r.invalidation);list(detail,'Still missing',r.missing);
 detail.append(el('h3','Confirmed source facts','label'));
 for(const fact of r.facts||[]){const b=el('blockquote',fact.text);b.append(sourceLink(fact.url||e.url,' Source'));detail.append(b);}
 detail.append(el('p',r.confidence||'Evidence support is separate from trading success.'),el('p',`First stored ${date(e.first_seen_at)} · Retrieved ${date(e.retrieved_at)} · ${e.backfill?'Historical/backfilled evidence':'Newly observed evidence'}`));
 detail.append(el('h3','Why this ranking','label'));for(const [key,value]of Object.entries(rank.components||{}))detail.append(el('p',`${key.replaceAll('_',' ')}: ${value>=0?'+':''}${value}`));detail.append(el('p',rank.meaning||'Research priority only.'));
 n.append(detail);return n;
}
function filtered(){const q=$('#search').value.trim().toLowerCase();return data.events.filter(e=>`${e.title} ${(e.tickers||[]).join(' ')} ${e.research?.takeaway||''}`.toLowerCase().includes(q));}
function metric(root,label,value,suffix='',scale=1){const n=el('div',label);n.append(el('strong',typeof value==='number'&&Number.isFinite(value)?(value*scale).toFixed(2)+suffix:'Unavailable'));root.append(n);}
function stockCard(symbol,privateStock=false){
 const n=el('article',undefined,'card');n.append(el('h2',symbol));
 const count=data.events.filter(e=>e.tickers.includes(symbol)).length;n.append(el('p',`${count} evidence records · ${privateStock?'Saved to your private backend watchlist':'Public research coverage'}`));
 const jobs=data.status[0]?.payload?.jobs||[],job=jobs.find(j=>j.name===`sec:${symbol}`);
 n.append(el('p',job?.last_success?`Company collection ${date(job.last_success)}`:'Queued for the next collection batch; no successful company collection yet.'));
 if(job?.last_error)n.append(el('p',`Collection issue: ${job.last_error}`));
 const b=el('button','Open company research');b.addEventListener('click',()=>showCompany(symbol));n.append(b);
 if(privateStock){const remove=el('button','Remove from watchlist');remove.addEventListener('click',async()=>{try{await api('/api/watchlist',{action:'remove',symbol});await loadWatchlist();render();}catch(e){$('#notice').textContent=e.message;}});n.append(remove);}
 return n;
}
function trend(root,symbol){
 const records=data.events.filter(e=>e.tickers.includes(symbol)&&['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'].includes(e.evidence_meta?.tag));
 const annual=records.filter(e=>{const m=e.evidence_meta;return(new Date(m.end)-new Date(m.start))/86400000>=350;});
 const unique=new Map();for(const e of annual.sort((a,b)=>a.published_at.localeCompare(b.published_at)))unique.set(e.evidence_meta.end,e);
 const series=[...unique.values()].sort((a,b)=>a.evidence_meta.end.localeCompare(b.evidence_meta.end)).slice(-5);
 if(series.length<2){root.append(el('p','A revenue trend chart requires at least two comparable annual periods.'));return;}
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 600 210');svg.setAttribute('role','img');svg.setAttribute('aria-label','Reported annual revenue by fiscal year');
 const max=Math.max(...series.map(e=>e.evidence_meta.value));if(!(max>0))return;
 series.forEach((e,i)=>{const h=Math.max(0,e.evidence_meta.value/max*150),x=30+i*110;const bar=document.createElementNS(svg.namespaceURI,'rect');bar.setAttribute('x',x);bar.setAttribute('y',170-h);bar.setAttribute('width',70);bar.setAttribute('height',h);bar.setAttribute('fill','#a5f0ba');const title=document.createElementNS(svg.namespaceURI,'title');title.textContent=`${e.evidence_meta.end}: $${Number(e.evidence_meta.value).toLocaleString()}`;bar.append(title);svg.append(bar);const label=document.createElementNS(svg.namespaceURI,'text');label.setAttribute('x',x);label.setAttribute('y',195);label.setAttribute('fill','#a8bab0');label.textContent=e.evidence_meta.end.slice(0,4);svg.append(label);});root.append(svg,el('p','Reported annual revenue; hover over a bar for the value. Dates are fiscal period ends, not earnings forecasts.'));
}
function showCompany(symbol){
 selected=symbol;$('#board').hidden=true;$('#company').hidden=false;const root=$('#company');root.replaceChildren();
 const back=el('button','← Back to board');back.addEventListener('click',()=>{selected=null;render();});root.append(back,el('h2',`${symbol} · Research dossier`));
 const mine=watchlist.includes(symbol),add=el('button',mine?'Saved to watchlist':'Save to my watchlist');add.disabled=mine;add.addEventListener('click',()=>saveStock(symbol));root.append(add);
 root.append(el('h3','Business performance','label'));trend(root,symbol);
 const ratios=data.financial_context[symbol]||[];
 const grid=el('div',undefined,'metric-grid');for(const m of ratios.slice(0,9)){metric(grid,`${m.label} · ${m.period_end}`,m.value,m.unit==='USD'?' USD':m.unit);const sources=el('p');for(const id of m.evidence_ids){const e=data.events.find(x=>x.id===id);if(e)sources.append(sourceLink(e.url,'Evidence ↗ '));}grid.append(sources);}root.append(grid);
 if(!ratios.length)root.append(el('p','Comparable financial ratios are not available yet; the collector must retrieve matched-period facts.'));
 root.append(el('h3','Market behavior','label'));const q=data.status[0]?.payload?.quantitative?.[symbol];
 if(q?.status==='available'){const g=el('div',undefined,'metric-grid');metric(g,'20-session realized volatility',q.realized_volatility_20,'%',100);metric(g,'60-session realized volatility',q.realized_volatility_60,'%',100);metric(g,'Latest return z-score',q.latest_return_zscore);metric(g,'20-session momentum',q.momentum_20,'%',100);metric(g,'60-session drawdown',q.drawdown_60,'%',100);metric(g,'Beta versus SPY',q.beta_60);root.append(el('p',`Historical IEX daily bars as of ${q.as_of_session}`),g);list(root,'Research flags',q.flags);}else root.append(el('p','Price-history statistics are unavailable. An authorized market-data feed is required; no values or forecasts are fabricated.'));
 root.append(el('h3','Expectations and catalyst','label'),el('p','Consensus gap unverified. No dated analyst consensus or confirmed upcoming earnings calendar is connected.'));
 const records=latest(data.events.filter(e=>e.tickers.includes(symbol)));const board=el('div',undefined,'board');for(const e of records.slice(0,12))board.append(card(e));root.append(board);
 if(!records.length)root.append(el('p','No company evidence yet. Save this stock and run collection; queued coverage is bounded.'));
}
function render(){
 if(selected){showCompany(selected);return;}const root=$('#board');root.hidden=false;$('#company').hidden=true;root.replaceChildren();const records=filtered();
 if(view==='watchlist'){
  heading('Your watchlist',user?'Saved stocks feed the autonomous collector. Company coverage rotates through a bounded universe.':'Sign in to save a private watchlist. These companies have public research coverage.');
  const form=el('form',undefined,'watch-add'),input=el('input');input.placeholder='Add ticker, e.g. TSLA';input.maxLength=10;input.required=true;input.setAttribute('aria-label','Stock ticker');const button=el('button','Save stock');form.append(input,button);form.addEventListener('submit',e=>{e.preventDefault();saveStock(input.value.trim().toUpperCase());});root.append(form);
  const symbols=user?watchlist:['AAPL','MSFT','NVDA'];for(const s of symbols)root.append(stockCard(s,Boolean(user)));if(!symbols.length)root.append(el('p','Your saved watchlist is empty. Add a stock to request backend coverage.'));
 }else if(view==='sources'){
  heading('Actual source health','Working integrations retrieve evidence. Licensed and unsupported entries are access requirements, not connected feeds.');
  for(const s of data.source_health||[]){const n=el('article',undefined,'card');n.append(el('h2',s.name),el('div',s.integration_status,'badge'),el('p',`${s.records} retained records · Last successful collection ${date(s.last_success)}`),el('p',s.capabilities||''));const age=s.last_success?(Date.now()-new Date(s.last_success))/3600000:Infinity;if(s.integration_status==='working integration'&&age>36)n.append(el('p','STALE: the last successful collection is over 36 hours old.'));list(n,'Current collection issues',s.errors);n.append(sourceLink(s.documentation_url,'Access documentation'));root.append(n);}
 }else if(view==='opportunities'){
  heading('Opportunity research board','Ranked evidence to investigate—not buy recommendations. Scores expose source support, freshness, comparisons, and missing context.');
  const candidates=latest(records.filter(e=>e.research?.ranking?.eligible_weekly));if(!candidates.length)root.append(el('div','No candidates meet the weekly evidence and freshness criteria. Historical research remains available in Research history.','empty'));
  for(const e of candidates.slice(0,15))root.append(card(e));
 }else if(view==='macro'){
  heading('Macro & policy','Official developments, financing mechanisms, and conditional scenarios. Speeches are distinguished from enacted decisions.');for(const e of latest(records.filter(e=>['systemic','political'].includes(e.research?.category))).slice(0,20))root.append(card(e));
 }else if(view==='history'){
  heading('Research history','Source revisions and historical analyses are retained. Realized outcomes are unavailable without point-in-time market prices; no backtest profitability is claimed.');
  for(const e of [...records].sort((a,b)=>b.published_at.localeCompare(a.published_at)).slice(0,60))root.append(card(e));
 }else{
  heading('Today’s research brief','The highest-priority evidence available, including historical context. Expand a card to inspect facts, calculations, and what could disprove the thesis.');
  for(const e of latest(records).slice(0,12))root.append(card(e));
 }
 if(!root.childNodes.length)root.append(el('div','No matching research is available. Try another search or inspect Source health.','empty'));
}
async function loadWatchlist(){if(!user){watchlist=[];return;}const result=await api('/api/watchlist');watchlist=result.watchlist;}
async function loadSession(){try{const s=await api('/api/session');user=s.user;if(!user){try{await api('/api/session',{action:'refresh'});user=(await api('/api/session')).user;}catch{}}await loadWatchlist();}catch{user=null;}$('#account-toggle').textContent=user?`Account: ${user.email}`:'Sign in / create account';$('#logout').hidden=!user;$('#auth-form').hidden=Boolean(user);}
async function saveStock(symbol){if(!user){$('#account').hidden=false;$('#auth-message').textContent='Sign in first to save a private backend watchlist.';$('#account').scrollIntoView();return;}try{await api('/api/watchlist',{action:'add',symbol});await loadWatchlist();$('#notice').textContent=`${symbol} saved in Supabase. It is queued for backend collection, subject to the active-universe limit.`;render();}catch(e){$('#notice').textContent=e.message;}}
async function load(){const b=$('#refresh');b.disabled=true;try{data=await api('/api/dashboard');$('#count').textContent=data.events.length;$('#candidate-count').textContent=latest(data.events.filter(e=>e.research?.ranking?.eligible_weekly)).length;const s=data.status[0];$('#freshness').textContent=s?`Last collection ${date(s.updated_at)} · ${s.payload.collection_note||s.payload.cadence?.replaceAll('_',' ')||'Schedule not verified'}`:'Awaiting first collection';const errors=s?.payload?.jobs?.filter(j=>j.last_error)||[];$('#notice').textContent=errors.length?`${errors.length} source jobs have collection issues. See Source health.`:'';}catch(e){$('#notice').textContent=e.message;$('#freshness').textContent='Research connection unavailable';}finally{render();b.disabled=false;}}
async function signIn(action){const b=$('#auth-form button');b.disabled=true;try{const r=await api('/api/session',{action,email:$('#email').value.trim(),password:$('#password').value});$('#password').value='';$('#auth-message').textContent=r.confirmation_required?'Check your email to confirm the account, then sign in.':'Signed in. Your watchlist is saved privately.';await loadSession();render();}catch(e){$('#auth-message').textContent=e.message;}finally{b.disabled=false;}}
$('#auth-form').addEventListener('submit',e=>{e.preventDefault();signIn('login');});$('#signup').addEventListener('click',()=>{if($('#auth-form').reportValidity())signIn('signup');});$('#logout').addEventListener('click',async()=>{await api('/api/session',{action:'logout'});await loadSession();render();});$('#account-toggle').addEventListener('click',()=>{$('#account').hidden=!$('#account').hidden;});
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.view;selected=null;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));render();}));$('#search').addEventListener('input',()=>{selected=null;render();});$('#refresh').addEventListener('click',load);
$('#collect').addEventListener('click',async()=>{if(!user){$('#account').hidden=false;$('#auth-message').textContent='Sign in to request a collection refresh.';return;}const b=$('#collect');b.disabled=true;$('#notice').textContent='Collecting official evidence. This can take a few minutes…';try{const result=await api('/api/collect',{});await load();$('#notice').textContent=result.status==='cooldown_or_running'?'Collection is already running or within its 15-minute cooldown.':`Collection completed: ${result.records} records retrieved. Check Source health for partial failures.`;}catch(e){$('#notice').textContent=e.message;}finally{b.disabled=false;}});
Promise.all([load(),loadSession()]).then(render);
