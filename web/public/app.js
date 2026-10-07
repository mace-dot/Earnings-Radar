'use strict';
let data = {events: [], status: [], weekly: [], financial_context: {}, source_health: []};
let view = 'brief', user = null, watchlist = [], selected = null, lane = 'all', ideas = [];
const $ = s => document.querySelector(s);
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined) n.textContent=text; if(cls)n.className=cls; return n; };
const evidenceUrl=e=>e.readable_url||e.url;
const evidenceTitle=e=>e.display_title||e.title;
let companyDetails={},strategyRequests=new Map();
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
 n.append(el('h2',r.takeaway||evidenceTitle(e)),el('h3','Why it matters','label'),el('p',r.mechanism||'Interpretation is not available.'));
 n.append(el('div',`Next step: ${r.next_step||'Read the primary source.'}`,'next-step'));
 const rank=r.ranking||{};n.append(el('p',`Research priority ${rank.score??'—'} · Published ${date(e.published_at)}`));
 if(e.display_value)n.append(el('p',`${evidenceTitle(e)} · ${e.display_value}`));
 n.append(sourceLink(evidenceUrl(e),e.source_label||'Read original source ↗'));
 const detail=el('details');detail.append(el('summary','Bull / bear case, calculations & evidence'));
 list(detail,'Bull case — conditional',r.bull);list(detail,'Bear case — conditional',r.bear);list(detail,'Counterevidence & uncertainty',r.counterevidence);
 detail.append(el('h3','Expectations versus reality','label'),el('p',r.expectations||'Unverified'),el('p',`Catalyst: ${r.catalyst||'Not confirmed'}`),el('p',`Horizon: ${r.horizon||'Unspecified'}`));
 for(const c of r.calculations||[]){detail.append(el('p',`${c.label}: ${typeof c.value==='number'?c.value.toFixed(2):'Unavailable'} ${c.unit||''}. ${c.explanation||''}`));for(const id of c.evidence_ids||[]){const source=data.events.find(x=>x.id===id);if(source)detail.append(sourceLink(evidenceUrl(source),`Calculation source: ${evidenceTitle(source)}`));}}
 list(detail,'What would invalidate the thesis',r.invalidation);list(detail,'Still missing',r.missing);
 detail.append(el('h3','Confirmed source facts','label'));
 for(const fact of r.facts||[]){const b=el('blockquote',fact.text);b.append(sourceLink(evidenceUrl(e),' Read supporting source'));detail.append(b);}
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
function showCompany(symbol,ready=false){
 if(!ready){openResearch(symbol);return;}
 selected=symbol;$('#board').hidden=true;$('#company').hidden=false;const root=$('#company');root.replaceChildren();
 const back=el('button','← Back to board');back.addEventListener('click',()=>{selected=null;render();});root.append(back,el('h2',`${symbol} · Research dossier`));
 appendPriceHistory(root,companyDetails[symbol]?.price_history);
 appendAssistant(root,symbol);
 const newsHealth=companyDetails[symbol]?.price_history?.news_status||[];
 for(const feed of newsHealth)root.append(el('p',`Company news feed: ${feed.name} · ${feed.status}${feed.last_error?' · '+feed.last_error:''}`));
 const strategies=companyDetails[symbol]?.strategies;
 if(strategies){root.append(el('h3','Automatic Up / Down assessment'));for(const d of ['up','down'])root.append(strategyCard(strategies[d]));}
 const mine=watchlist.includes(symbol),add=el('button',mine?'Saved to watchlist':'Save to my watchlist');add.disabled=mine;add.addEventListener('click',()=>saveStock(symbol));root.append(add);
 root.append(el('h3','Business performance','label'));trend(root,symbol);
 const ratios=data.financial_context[symbol]||[];
 const grid=el('div',undefined,'metric-grid');for(const m of ratios.slice(0,9)){metric(grid,`${m.label} · ${m.period_end}`,m.value,m.unit==='USD'?' USD':m.unit);const sources=el('p');for(const id of m.evidence_ids){const e=data.events.find(x=>x.id===id);if(e)sources.append(sourceLink(evidenceUrl(e),'Read filing ↗ '));}grid.append(sources);}root.append(grid);
 if(!ratios.length)root.append(el('p','Comparable financial ratios are not available yet; the collector must retrieve matched-period facts.'));
 root.append(el('h3','Market behavior','label'));const q=companyDetails[symbol]?.price_history?.statistics||data.status[0]?.payload?.quantitative?.[symbol];
 if(q?.status==='available'){const g=el('div',undefined,'metric-grid');metric(g,'20-session realized volatility',q.realized_volatility_20,'%',100);metric(g,'60-session realized volatility',q.realized_volatility_60,'%',100);metric(g,'Latest return z-score',q.latest_return_zscore);metric(g,'20-session momentum',q.momentum_20,'%',100);metric(g,'60-session drawdown',q.drawdown_60,'%',100);metric(g,'Beta versus SPY',q.beta_60);root.append(el('p',`Historical daily bars as of ${q.as_of_session}`),g);list(root,'Research flags',q.flags);}else root.append(el('p','Price statistics need an authorized feed and at least 61 daily bars. Available charts and feed status appear above; company financial analysis continues independently.'));
 root.append(el('h3','Expectations and catalyst','label'),el('p','Consensus gap unverified. No dated analyst consensus or confirmed upcoming earnings calendar is connected.'));
 const records=latest(data.events.filter(e=>e.tickers.includes(symbol)));const board=el('div',undefined,'board');for(const e of records.slice(0,12))board.append(card(e));root.append(board);
 if(!records.length)root.append(el('p','No company evidence yet. Save this stock and run collection; queued coverage is bounded.'));
}
function render(){
 renderIdeas();if(selected){showCompany(selected,true);return;}const root=$('#board');root.hidden=false;$('#company').hidden=true;root.replaceChildren();const records=filtered();
 if(view==='watchlist'){
  heading('Your watchlist',user?'Saved stocks feed the autonomous collector. Company coverage rotates through a bounded universe.':'Sign in to save a private watchlist. These companies have public research coverage.');
  const form=el('form',undefined,'watch-add'),input=el('input');input.placeholder='Add ticker, e.g. TSLA';input.maxLength=10;input.required=true;input.setAttribute('aria-label','Stock ticker');const button=el('button','Save stock');form.append(input,button);form.addEventListener('submit',e=>{e.preventDefault();saveStock(input.value.trim().toUpperCase());});root.append(form);
  const symbols=user?watchlist:(data.move_board||[]).map(b=>b.symbol);for(const s of symbols){const b=(data.move_board||[]).find(x=>x.symbol===s);root.append(b?moveTile(b):stockCard(s,Boolean(user)));}if(!symbols.length)root.append(el('p','Your saved watchlist is empty. Add a stock to request backend coverage.'));
 }else if(view==='discover'){
 heading('Discover companies','The scanner finds recent official disclosures automatically. Filing activity is a research lead, not a predicted price move.');
 const scan=data.status[0]?.payload?.discovery;
 root.append(el('p',scan?.date?`SEC daily index: ${scan.date}`:'Daily discovery has not completed yet.'));
 for(const c of scan?.candidates||[]){const n=el('article',undefined,'card');n.append(el('h2',c.symbol),el('p',`${c.name} · ${c.discovery_form} filed ${c.discovery_date}`));const b=el('button','Research this company');b.addEventListener('click',()=>openResearch(c.symbol));n.append(b);root.append(n);}
 }else if(view==='track'){
 heading('Track record','Immutable research snapshots record what was known. No validated price forecasts or trading win rate are available yet.');
 loadTrack(root);
 }else if(view==='sources'){
  heading('Actual source health','Working integrations retrieve evidence. Licensed and unsupported entries are access requirements, not connected feeds.');
  for(const s of data.source_health||[]){const n=el('article',undefined,'card');n.append(el('h2',s.name),el('div',s.integration_status,'badge'),el('p',`${s.records} retained records · Last successful collection ${date(s.last_success)}`),el('p',s.capabilities||''));const age=s.last_success?(Date.now()-new Date(s.last_success))/3600000:Infinity;if(s.integration_status==='working integration'&&age>36)n.append(el('p','STALE: the last successful collection is over 36 hours old.'));list(n,'Current collection issues',s.errors);n.append(sourceLink(s.documentation_url,'Access documentation'));root.append(n);}
 }else if(view==='opportunities'){
  heading('Opportunity research board','Ranked evidence to investigate—not buy recommendations. Scores expose source support, freshness, comparisons, and missing context.');
  const candidates=latest(records.filter(e=>e.research?.ranking?.eligible_weekly));if(!candidates.length)root.append(el('div','No candidates meet the weekly evidence and freshness criteria. Historical research remains available in Research history.','empty'));
  for(const e of candidates.slice(0,15))root.append(card(e));
 }else if(view==='macro'){
  heading('Market weather','Watch for funding trouble and bigger price swings. Missing information means unknown, not calm.');root.append(weatherPanel());for(const e of latest(records.filter(e=>['systemic','political'].includes(e.research?.category))).slice(0,20))root.append(card(e));
 }else if(view==='history'){
  heading('Research history','Source revisions and historical analyses are retained. Realized outcomes are unavailable without point-in-time market prices; no backtest profitability is claimed.');
  for(const e of [...records].sort((a,b)=>b.published_at.localeCompare(a.published_at)).slice(0,60))root.append(card(e));
 }else{
  heading(lane==='stress'?'Funding watch':lane==='volatility'?'Big-swing watch':'Your stock pick board',lane==='stress'?'Company funding questions are clues to investigate, not forecasts of a market-wide crisis.':lane==='volatility'?'Look for changing price behavior and a reason the next move could matter. A quiet stock is not automatically ready to break out.':'Pick a company. Explore an up or down case. Check the evidence before deciding what to do.');
  let companies=(data.move_board||[]).filter(b=>!$('#search').value.trim()||`${b.symbol} ${b.name} ${b.business}`.toLowerCase().includes($('#search').value.trim().toLowerCase()));
  if(lane==='stress'){root.append(weatherPanel());companies=companies.filter(b=>b.stress_flags?.length);}
  if(lane==='volatility'){companies=companies.filter(b=>['Unusual daily move','Movement picking up','Quiet stretch'].includes(b.movement));if(!companies.length)root.append(el('div','We need connected price history to screen for changing volatility. Company research is available on All companies; no imminent move is inferred from headlines.','empty'));}
  for(const b of companies)root.append(moveTile(b));
 }
 $('#lanes').hidden=view!=='brief';renderIdeas();if(!root.childNodes.length)root.append(el('div',lane==='stress'?'No company funding flags are established in the available data. Market-wide crisis risk is still unknown.':'No matching company research is available. Try another search or check Data checks.','empty'));
}
async function loadWatchlist(){if(!user){watchlist=[];return;}const result=await api('/api/watchlist');watchlist=result.watchlist;}
async function loadSession(){try{const s=await api('/api/session');user=s.user;if(!user){try{await api('/api/session',{action:'refresh'});user=(await api('/api/session')).user;}catch{}}await loadWatchlist();if(user){ideas=(await api('/api/ideas')).ideas.map(i=>({...i,saved:true}));const saved=ideas.slice();void(async()=>{for(const i of saved){if(!user)break;await fetchAssessment(i);}})();}}catch{user=null;}$('#account-toggle').textContent=user?`Account: ${user.email}`:'Sign in / create account';$('#logout').hidden=!user;$('#auth-form').hidden=Boolean(user);}
async function saveStock(symbol){if(!user){$('#account').hidden=false;$('#auth-message').textContent='Sign in first to save a private backend watchlist.';$('#account').scrollIntoView();return;}try{await api('/api/watchlist',{action:'add',symbol});await loadWatchlist();$('#notice').textContent=`${symbol} saved in Supabase. It is queued for backend collection, subject to the active-universe limit.`;render();}catch(e){$('#notice').textContent=e.message;}}
async function load(){const b=$('#refresh');b.disabled=true;try{data=await api('/api/dashboard');$('#count').textContent=(data.move_board||[]).length;$('#stress-count').textContent=(data.move_board||[]).filter(b=>b.stress_flags?.length).length;$('#candidate-count').textContent=latest(data.events.filter(e=>e.research?.ranking?.eligible_weekly)).length;const s=data.status[0];$('#freshness').textContent=s?`Research updated ${date(s.updated_at)} · daily updates, rotating company coverage`:'Awaiting first collection';const errors=s?.payload?.jobs?.filter(j=>j.last_error)||[];$('#notice').textContent=errors.length?`Some data feeds are unavailable. Open Data checks to see what is connected.`:'';}catch(e){$('#notice').textContent=e.message;$('#freshness').textContent='Research connection unavailable';}finally{render();b.disabled=false;}}
async function signIn(action){const b=$('#auth-form button');b.disabled=true;try{const r=await api('/api/session',{action,email:$('#email').value.trim(),password:$('#password').value});$('#password').value='';$('#auth-message').textContent=r.confirmation_required?'Check your email to confirm the account, then sign in.':'Signed in. Your watchlist is saved privately.';await loadSession();render();}catch(e){$('#auth-message').textContent=e.message;}finally{b.disabled=false;}}
$('#auth-form').addEventListener('submit',e=>{e.preventDefault();signIn('login');});$('#signup').addEventListener('click',()=>{if($('#auth-form').reportValidity())signIn('signup');});$('#logout').addEventListener('click',async()=>{await api('/api/session',{action:'logout'});ideas=[];await loadSession();render();});$('#account-toggle').addEventListener('click',()=>{$('#account').hidden=!$('#account').hidden;});
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.view;selected=null;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));render();}));$('#search').addEventListener('input',()=>{selected=null;render();clearTimeout(searchTimer);searchTimer=setTimeout(searchDirectory,300);});$('#refresh').addEventListener('click',load);
$('#collect').addEventListener('click',async()=>{if(!user){$('#account').hidden=false;$('#auth-message').textContent='Sign in to request a collection refresh.';return;}const b=$('#collect');b.disabled=true;$('#notice').textContent='Collecting official evidence. This can take a few minutes…';try{const result=await api('/api/collect',{});await load();$('#notice').textContent=result.status==='cooldown_or_running'?'Collection is already running or within its 15-minute cooldown.':`Collection completed: ${result.records} records retrieved. Check Source health for partial failures.`;}catch(e){$('#notice').textContent=e.message;}finally{b.disabled=false;}});
Promise.all([load(),loadSession()]).then(render);

function moveTile(b){
 const n=el('article',undefined,'card tile'),top=el('div',undefined,'tile-head');
 top.append(el('div',b.symbol.slice(0,1),'company-avatar'));const title=el('div');title.append(el('div',b.symbol,'tile-name'),el('div',b.name,'tile-company'));top.append(title);n.append(top);
 const plain=b.business.replace(/\$(-?[\d,]+(?:\.\d+)?)/g,(_,v)=>compactMoney(Number(v.replaceAll(',',''))));n.append(el('div',b.business_signal,'tile-status'),el('h3','What changed','label'),el('h2',plain));
 n.append(el('div',b.movement,'move-label'),el('p',b.movement_note,'small-copy'));
 for(const f of b.stress_flags||[])n.append(el('div',`${f.text} Reported period: ${f.period_end}.`,'stress-flag'));
 n.append(el('p',`Next event: ${b.catalyst||'Date not confirmed.'}`,'small-copy'));
 const choices=el('div',undefined,'direction-buttons');
 for(const [direction,label] of [['up','↑ Up case'],['down','↓ Down case']]){
  const chosen=ideas.some(i=>i.symbol===b.symbol&&i.direction===direction),button=el('button',label,`${direction}${chosen?' chosen':''}`);button.setAttribute('aria-pressed',String(chosen));button.setAttribute('aria-label',`Explore ${b.symbol} ${direction} research case`);
  button.addEventListener('click',()=>chooseIdea(b,direction));choices.append(button);
 }
 n.append(choices);const details=el('button','See the evidence & company details','detail-button');details.addEventListener('click',()=>showCompany(b.symbol));n.append(details);return n;
}
function weatherPanel(){
 const n=el('section',undefined,'stress-overview');n.append(el('h3','Can the market get the cash it needs?'),el('p','A liquidity problem happens when cash or willing buyers become hard to find. One company’s weak finances do not prove a system-wide crisis.'));
 const grid=el('div',undefined,'weather-grid');
 for(const [title,text]of [['Company funding','Financial filings can reveal cash or interest-payment concerns. Check the period and the details.'],['Banks & funding markets','Unknown: current interbank funding and credit-spread series are not connected.'],['Trading conditions','Unknown: current spreads, market depth, and options pricing are not connected.']]){const box=el('div');box.append(el('strong',title),el('span',text));grid.append(box);}
 n.append(grid,el('p','Hidden edge: not established. We need evidence that differs from documented market expectations.'));return n;
}
async function chooseIdea(b,direction){
 const existing=ideas.find(i=>i.symbol===b.symbol&&i.direction===direction);
 if(existing){if(existing.saved&&user){try{await api('/api/ideas',{action:'remove',symbol:b.symbol,direction});}catch(e){$('#idea-message').textContent=e.message;return;}}ideas=ideas.filter(i=>i!==existing);}
 else{if(ideas.length>=20){$('#idea-message').textContent='Keep up to 20 research ideas.';return;}const idea={symbol:b.symbol,direction,evidence_id:b.evidence_id,saved:false,assessment:companyDetails[b.symbol]?.strategies?.[direction]};ideas.push(idea);
 if(!idea.assessment)fetchAssessment(idea);}
 render();$('#idea-message').textContent='Automatic analysis compares the selected direction with supporting and opposing evidence.';
}
function renderIdeas(){
 const root=$('#idea-list');root.replaceChildren();$('#lineup-mobile').hidden=!ideas.length;$('#lineup-mobile').textContent=`${ideas.length} research ${ideas.length===1?'idea':'ideas'} · View lineup`;
 if(!ideas.length)root.append(el('p','Your lineup is empty. Try an Up or Down case on a company.','small-copy'));
 for(const idea of ideas){const e=data.events.find(x=>x.id===idea.evidence_id),r=e?.research||{},n=el('article',undefined,'idea-entry');n.append(el('strong',`${idea.symbol} · ${idea.direction==='up'?'↑ Up / call research':'↓ Down / put research'}`));
  if(idea.assessment)n.append(strategyCard(idea.assessment));else n.append(el('p',idea.error||'Automatically analysing financial evidence and market statistics…'));
  n.append(el('p',idea.saved?'Saved privately to your account':'Not saved yet'));
  const remove=el('button','Remove');remove.addEventListener('click',()=>chooseIdea({symbol:idea.symbol,evidence_id:idea.evidence_id},idea.direction));n.append(remove);root.append(n);
 }
 const explanation=$('#idea-explanation');explanation.replaceChildren();if(ideas.length)explanation.append(el('div','The backend builds each case for you. Company research continues with partial data; selecting a specific option still needs fresh quotes and confirmed timing.','explanation-box'));
}
$('#save-ideas').addEventListener('click',async()=>{
 if(!user){$('#account').hidden=false;$('#auth-message').textContent='Sign in to save your research lineup privately.';$('#idea-message').textContent='Sign in first. Your current ideas stay on this page.';return;}
 const b=$('#save-ideas');b.disabled=true;try{for(const i of ideas){await api('/api/ideas',{action:'save',symbol:i.symbol,direction:i.direction,evidence_id:i.evidence_id});i.saved=true;}renderIdeas();$('#idea-message').textContent='Ideas saved to your account. No trade was placed.';}catch(e){$('#idea-message').textContent=e.message;}finally{b.disabled=false;}
});
document.querySelectorAll('[data-lane]').forEach(b=>b.addEventListener('click',()=>{lane=b.dataset.lane;view='brief';selected=null;document.querySelectorAll('[data-lane]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view==='brief'));render();}));
$('#terms-toggle').addEventListener('click',()=>{$('#terms').hidden=!$('#terms').hidden;$('#terms-toggle').setAttribute('aria-expanded',String(!$('#terms').hidden));});

function compactMoney(v){if(!Number.isFinite(v))return'Unavailable';const sign=v<0?'-':'';const n=Math.abs(v);return sign+'$'+(n>=1e9?(n/1e9).toFixed(1)+'B':n>=1e6?(n/1e6).toFixed(1)+'M':n.toLocaleString());}
$('#option-math')?.addEventListener('submit',e=>{
 e.preventDefault();try{
  const fields=['strike','premium','quantity','target'];if(fields.some(k=>!$('#option-'+k).value.trim()))throw new Error('Enter every value from your option quote or hypothetical scenario.');
  const input=Object.fromEntries(fields.map(k=>[k,Number($('#option-'+k).value)]));input.type=$('#option-type').value;
  const r=optionScenario(input);$('#option-result').textContent=`Total premium paid: $${r.cost.toFixed(2)}. Maximum loss: $${r.maxLoss.toFixed(2)}. Expiration break-even: ${r.breakEven>=0?'$'+r.breakEven.toFixed(2):'not achievable at a nonnegative stock price'}. At your stock-price scenario: ${r.profitLoss>=0?'gain':'loss'} of $${Math.abs(r.profitLoss).toFixed(2)}, before fees.`;
 }catch(error){$('#option-result').textContent=error.message;}
});

$('#lineup-mobile').addEventListener('click',()=>$('#idea-panel').scrollIntoView?.({behavior:'smooth',block:'start'}));

let searchTimer, searchVersion=0;
async function searchDirectory(){
 const q=$('#search').value.trim(),version=++searchVersion,root=$('#directory-results');root.replaceChildren();if(!q)return;
 try{const result=await api('/api/directory?q='+encodeURIComponent(q));if(version!==searchVersion)return;
 root.append(el('p','Official company directory · select a company to research automatically'));
 for(const c of result.companies){const b=el('button',`${c.symbol} · ${c.name}${c.active?'':' · inactive'}`);b.disabled=!c.active;b.addEventListener('click',()=>openResearch(c.symbol));root.append(b);}
 if(!result.companies.length)root.append(el('p','No official SEC directory match. Global and private companies may not be covered.'));
 }catch(e){root.textContent=e.message;}
}
async function openResearch(symbol){
 $('#notice').textContent=`Researching ${symbol}: retrieving official filings and financial facts…`;$('#search').value='';$('#directory-results').replaceChildren();
 try{const job=await api('/api/research',{symbol});const result=await api('/api/company?symbol='+encodeURIComponent(symbol));
 companyDetails[symbol]=result;
 const ids=new Set(result.events.map(e=>e.id));data.events=[...result.events,...data.events.filter(e=>!ids.has(e.id))];Object.assign(data.financial_context,result.financial_context);
 if(data.status[0])data.status[0].payload.quantitative={...data.status[0].payload.quantitative,[symbol]:result.price_history?.statistics||{}};
 data.move_board=[...(result.move_board||[]),...(data.move_board||[]).filter(b=>b.symbol!==symbol)];
 $('#notice').textContent=`${symbol}: ${job.status}. ${result.events.length} retained evidence records. Options decision: WAIT until required market inputs are connected.`;if(result.events.length)showCompany(symbol,true);else{$('#company').hidden=false;$('#board').hidden=true;$('#company').replaceChildren(el('h2',symbol),el('p',`Research status: ${job.status}. No supported company evidence retrieved yet. Try again after the retry interval.`));}
 }catch(e){$('#notice').textContent=e.message;}
}
function appendAssistant(root,symbol){
 const box=el('section',undefined,'card');box.append(el('h3','Ask your research assistant'),el('p','Answers explain collected evidence in plain language. Current engine: computed statistics and financial evidence. Hosted AI explanations are optional.'));
 const form=el('form'),input=el('input'),button=el('button','Explain');input.placeholder='What changed? What are the cash risks?';input.maxLength=400;input.required=true;input.setAttribute('aria-label','Company research question');form.append(input,button);const output=el('div');output.setAttribute('role','status');
 form.addEventListener('submit',async e=>{e.preventDefault();button.disabled=true;output.textContent='Reading the evidence…';try{const result=await api('/api/assistant',{symbol,question:input.value});output.replaceChildren(el('p',result.answer),el('p',result.engine));for(const c of result.citations||[])output.append(sourceLink(c.url,c.quote));list(output,'What would change this assessment',result.invalidation);list(output,'Still missing',result.missing);}catch(err){output.textContent=err.message;}finally{button.disabled=false;}});box.append(form,output);root.append(box);
}
async function loadTrack(root){
 try{const result=await api('/api/track-record');if(view!=='track')return;root.append(el('p',result.forecast_status));for(const r of result.snapshots){const n=el('article',undefined,'card');n.append(el('h2',r.symbol),el('p',date(r.created_at)),el('p',`Decision: ${r.payload.action.toUpperCase()} · ${r.payload.source_ids.length} source records · ${r.engine_version}`),el('p',r.payload.summary?.changed||'Research evidence saved for later comparison.'));const b=el('button','Open company');b.addEventListener('click',()=>openResearch(r.symbol));n.append(b);root.append(n);}if(!result.snapshots.length)root.append(el('p','The first completed research job will create a snapshot.'));}catch(e){root.append(el('p',e.message));}
}

async function fetchAssessment(idea){
 const key=idea.symbol+':'+idea.direction;
 try{let pending=strategyRequests.get(key);if(!pending){pending=api('/api/strategy',{symbol:idea.symbol,direction:idea.direction});strategyRequests.set(key,pending);}
 idea.assessment=await pending;renderIdeas();}catch(e){idea.error=e.message;renderIdeas();}finally{strategyRequests.delete(key);}
}
function strategyCard(s){
 const n=el('section',undefined,'strategy-card');n.append(el('h3',`${s.direction==='up'?'↑ Up / call case':'↓ Down / put case'} · ${s.decision}`),el('p',s.summary),el('p',s.mechanism));
 list(n,'What supports this case',(s.supporting||[]).map(x=>x.text));list(n,'What argues against it',(s.counterevidence||[]).map(x=>x.text));list(n,'Company funding concerns',(s.funding_risks||[]).map(x=>x.text));
 n.append(el('p',`Option selection: ${s.contract_decision||'WAIT'}. ${s.catalyst||''}`));
 for(const r of s.scenarios||[])n.append(el('p',`${r.sessions}-session movement sensitivity: $${r.lower.toFixed(2)}–$${r.upper.toFixed(2)} around $${r.reference_price.toFixed(2)}. Historical-volatility scenario; not a price target or probability.`));
 list(n,'What would change the assessment',s.invalidation);list(n,'Inputs still needed for contract selection',s.missing);
 if(s.reported_developments?.length){n.append(el('h4','Recent reports to corroborate'));for(const item of s.reported_developments)n.append(sourceLink(item.url,`${item.title} · ${date(item.published_at)}`));}
 const details=el('details');details.append(el('summary','Methods and supporting sources'),el('p',s.methods||''));for(const c of s.citations||[])details.append(sourceLink(c.url,c.title));n.append(details);return n;
}
function appendPriceHistory(root,h){
 const box=el('section',undefined,'price-history');box.append(el('h3','Price action history'));
 if(!h?.bars?.length){box.append(el('p',h?.reason||'No authorized price-history connection is configured. Company financial research remains available.'));root.append(box);return;}
 box.append(el('p',`${h.provider} · ${h.feed} · ${h.currency} · ${h.cadence} · ${h.status==='stale'?'STALE CACHE · ':''}last session ${h.bars.at(-1).session}`),el('p',h.volume_scope),el('p',`Adjustments: ${h.adjustment} · retrieved ${date(h.retrieved_at)}`));
 const controls=el('div',undefined,'chart-controls'),chart=el('div');for(const [label,size]of [['1M',21],['3M',63],['6M',126],['1Y',252]]){const b=el('button',label);b.disabled=h.bars.length<size;b.addEventListener('click',()=>drawPriceChart(chart,h.bars.slice(-size)));controls.append(b);}
 box.append(controls,chart);drawPriceChart(chart,h.bars.slice(-Math.min(63,h.bars.length)));
 const q=h.statistics||{},grid=el('div',undefined,'metric-grid');metric(grid,'20-session price change',q.momentum_20,'%',100);metric(grid,'Annualized recent volatility',q.realized_volatility_20,'%',100);metric(grid,'14-session average price range',q.atr_14,' USD');metric(grid,'Volume / prior 20-session average',q.volume_ratio_20,'x');metric(grid,'60-session drawdown',q.drawdown_60,'%',100);box.append(grid,el('p','Historical measures describe what happened. They do not establish the next price direction.'));root.append(box);
}
function drawPriceChart(root,bars){
 root.replaceChildren();const first=bars[0],last=bars.at(-1);if(!first||bars.length<2)return;
 const values=bars.map(b=>b.c),low=Math.min(...values),high=Math.max(...values),range=high-low||1;
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 600 230');svg.setAttribute('role','img');svg.setAttribute('aria-label',`Daily closing prices from ${first.session} to ${last.session}; last close $${last.c.toFixed(2)}.`);
 const line=document.createElementNS(svg.namespaceURI,'polyline');line.setAttribute('points',bars.map((b,i)=>`${20+i*560/(bars.length-1)},${190-(b.c-low)/range*160}`).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','#a5f0ba');line.setAttribute('stroke-width','3');svg.append(line);
 root.append(svg,el('p',`${first.session} → ${last.session} · last close $${last.c.toFixed(2)} · period return ${((last.c/first.c-1)*100).toFixed(2)}% · closing-price range $${low.toFixed(2)}–$${high.toFixed(2)}`));
 const details=el('details');details.append(el('summary','Accessible price table'));const table=el('table'),head=el('tr');for(const name of ['Session','Close','Volume'])head.append(el('th',name));table.append(head);for(const b of bars){const r=el('tr');r.append(el('td',b.session),el('td',b.c.toFixed(2)),el('td',Number(b.v).toLocaleString()));table.append(r);}details.append(table);root.append(details);
}
