import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parseHTML} from 'linkedom';
const {document,window}=parseHTML(readFileSync(new URL('../public/index.html',import.meta.url),'utf8'));
const event={id:'a'.repeat(64),provider:'sec_fundamentals',provider_event_id:'a',title:'AAPL results',url:'https://www.sec.gov/test',institution:'SEC',published_at:'2026-10-05T00:00:00Z',retrieved_at:'2026-10-06T00:00:00Z',first_seen_at:'2026-10-06T00:00:00Z',tickers:['AAPL'],evidence_meta:{tag:'NetIncomeLoss',value:120,start:'2026-07-01',end:'2026-09-30'},research:{takeaway:'Profit improved, but cash conversion needs checking.',mechanism:'Recurring profit can support operating flexibility.',next_step:'Compare cash flow.',facts:[{text:'<img src=x onerror=steal()>',url:'javascript:alert(1)'}],bull:['If cash backs the improvement.'],bear:['One-off gains may reverse.'],ranking:{score:50,eligible_weekly:true,components:{source_support:20,missing_expectations:-10}},calculations:[]}};
const payload={events:[event],status:[{updated_at:'2026-10-06T00:00:00Z',payload:{jobs:[],cadence:'daily_scheduled'}}],weekly:[event.id],financial_context:{AAPL:[]},source_health:[{id:'wsj',name:'Wall Street Journal',integration_status:'licensed access required',records:0,errors:[],documentation_url:'https://www.wsj.com'}]};
payload.move_board=[{symbol:'AAPL',name:'Apple',evidence_id:event.id,business:'Profit improved, but cash conversion needs checking.',business_signal:'Business growing',movement:'Price data needed',movement_note:'Price history is not connected.',stress_flags:[],catalyst:'Date not confirmed.'}];
const calls=[];
const sandbox={document,window,URL,Date,console,setTimeout,fetch:async(path,options)=>{calls.push({path,options});let d=path==='/api/dashboard'||path.startsWith('/api/company')?payload:path==='/api/research'?{status:'cached'}:path==='/api/session'?{user:null}:{watchlist:[]};if(options&&path==='/api/session')return{ok:false,json:async()=>({error:'Sign in'})};return{ok:true,json:async()=>d};}};
vm.runInNewContext(readFileSync(new URL('../public/options.js',import.meta.url),'utf8'),sandbox);
vm.runInNewContext(readFileSync(new URL('../public/app.js',import.meta.url),'utf8'),sandbox);
await new Promise(resolve=>setTimeout(resolve,30));
assert.match(document.querySelector('#board').textContent,/Profit improved/);
assert.match(document.querySelector('#board').textContent,/What changed/);
assert.equal(document.querySelector('#board img'),null);
assert.equal(document.querySelector('[href^="javascript:"]'),null);
for(const view of ['opportunities','watchlist','macro','history','sources','brief']){
 document.querySelector(`[data-view="${view}"]`).dispatchEvent(new window.Event('click'));
 assert.ok(document.querySelector('#view-heading').textContent.length>0);
}
document.querySelector('[data-view="sources"]').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#board').textContent,/licensed access required/);
document.querySelector('[data-view="brief"]').dispatchEvent(new window.Event('click'));
document.querySelector('.detail-button').dispatchEvent(new window.Event('click'));
await new Promise(resolve=>setTimeout(resolve,30));
assert.match(document.querySelector('#company').textContent,/AAPL.*Research dossier/);
assert.match(document.querySelector('#company').textContent,/Price statistics need an authorized feed/);
document.querySelector('#collect').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#auth-message').textContent,/Sign in/);
assert.ok(!calls.some(c=>c.path==='/api/collect'));
document.querySelector('[data-view="brief"]').dispatchEvent(new window.Event('click'));
document.querySelector('.direction-buttons .up').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#idea-list').textContent,/AAPL.*Up.*call research/);
document.querySelector('#save-ideas').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#idea-message').textContent,/Sign in first/);
document.querySelector('[data-lane="volatility"]').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#board').textContent,/need connected price history/);
document.querySelector('[data-lane="stress"]').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#board').textContent,/Unknown.*current interbank/s);
console.log('UI smoke passed: navigation, company dossier, missing-data states, unsafe-content handling and authenticated collection gate');

const scenario=vm.runInNewContext("optionScenario({type:'call',strike:100,premium:2,quantity:1,target:105})",sandbox);assert.equal(scenario.profitLoss,300);assert.equal(scenario.maxLoss,200);assert.equal(scenario.breakEven,102);
const put=vm.runInNewContext("optionScenario({type:'put',strike:100,premium:2,quantity:2,target:90})",sandbox);assert.equal(put.profitLoss,1600);assert.equal(put.maxLoss,400);
assert.throws(()=>vm.runInNewContext("optionScenario({type:'call',strike:100,premium:2,quantity:1.5,target:105})",sandbox));
assert.equal(vm.runInNewContext("optionScenario({type:'call',strike:100,premium:2,quantity:1,target:99}).profitLoss",sandbox),-200);
// Broad search requests server identifiers rather than filtering the original board.
sandbox.fetch=async(path,options)=>{
 calls.push({path,options});
 const d=path.startsWith('/api/directory')?{companies:[{symbol:'TSLA',name:'Tesla, Inc.',active:true}]}:
 path==='/api/research'?{status:'complete'}:
 path.startsWith('/api/company')?{events:[{...event,tickers:['TSLA']}],financial_context:{TSLA:[]},move_board:[]}:
 path==='/api/assistant'?{engine:'deterministic evidence assistant',answer:'Cash risks require matched-period evidence.',citations:[{url:'https://www.sec.gov/test',quote:'Reported cash'}],missing:['Option quotes'],invalidation:[]}:
 path==='/api/track-record'?{forecast_status:'No validated forecasts.',snapshots:[]}:{watchlist:[]};
 return{ok:true,json:async()=>d};
};
sandbox.clearTimeout=clearTimeout;
document.querySelector('#search').value='Tesla';
document.querySelector('#search').dispatchEvent(new window.Event('input'));
await new Promise(resolve=>setTimeout(resolve,350));
assert.match(document.querySelector('#directory-results').textContent,/TSLA.*Tesla/);
document.querySelector('#directory-results button').dispatchEvent(new window.Event('click'));
await new Promise(resolve=>setTimeout(resolve,30));
assert.match(document.querySelector('#company').textContent,/TSLA.*Research dossier/);
assert.ok(calls.some(c=>c.path==='/api/research'&&JSON.parse(c.options.body).symbol==='TSLA'));
const form=document.querySelector('#company form');form.querySelector('input').value='What are the cash risks?';form.dispatchEvent(new window.Event('submit'));
await new Promise(resolve=>setTimeout(resolve,30));
assert.match(document.querySelector('#company').textContent,/Cash risks require matched-period evidence/);
document.querySelector('[data-view="track"]').dispatchEvent(new window.Event('click'));
await new Promise(resolve=>setTimeout(resolve,30));
assert.match(document.querySelector('#board').textContent,/No validated forecasts/);
console.log('Autonomous UI smoke passed: name search, automatic research, cited assistant and honest track record');
const automaticCase={direction:'down',decision:'WATCH',contract_decision:'WAIT',summary:'The downward case has mixed financial evidence.',mechanism:'Weak cash conversion can create financing pressure.',supporting:[{text:'Operating cash flow declined.'}],counterevidence:[{text:'Revenue grew.'}],funding_risks:[],scenarios:[],invalidation:['Cash conversion recovers.'],missing:['Fresh option quotes'],citations:[],methods:'Matched-period financial measures.'};
const previousFetch=sandbox.fetch;
sandbox.fetch=async(path,options)=>path==='/api/strategy'?(calls.push({path,options}),{ok:true,json:async()=>automaticCase}):previousFetch(path,options);
vm.runInNewContext("chooseIdea({symbol:'TSLA',evidence_id:'a'.repeat(64)},'down')",sandbox);
await new Promise(resolve=>setTimeout(resolve,30));
assert.match(document.querySelector('#idea-list').textContent,/Operating cash flow declined/);
assert.match(document.querySelector('#idea-list').textContent,/Revenue grew/);
assert.doesNotMatch(document.querySelector('#idea-list').textContent,/Build a documented direction thesis/);
const chartBars=Array.from({length:70},(_,i)=>({session:new Date(Date.UTC(2026,0,1+i)).toISOString().slice(0,10),c:100+i*.2,v:1000}));
sandbox.chartFixture={status:'available',provider:'Fixture provider',feed:'Fixture feed',currency:'USD',cadence:'completed sessions',volume_scope:'Fixture volume',adjustment:'fixture',retrieved_at:'2026-04-01T00:00:00Z',bars:chartBars,statistics:{}};
vm.runInNewContext("appendPriceHistory(document.querySelector('#company'),chartFixture)",sandbox);
assert.match(document.querySelector('#company').textContent,/period return/);
assert.ok(document.querySelector('#company svg[role="img"]'));
assert.match(document.querySelector('#company').textContent,/Accessible price table/);
console.log('Strategy/chart UI smoke passed: automatic direction assessment, counterevidence and accessible price history');
