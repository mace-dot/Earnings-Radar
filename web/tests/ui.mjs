import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parseHTML} from 'linkedom';
const {document,window}=parseHTML(readFileSync(new URL('../public/index.html',import.meta.url),'utf8'));
const event={id:'a'.repeat(64),provider:'sec_fundamentals',provider_event_id:'a',title:'AAPL results',url:'https://www.sec.gov/test',institution:'SEC',published_at:'2026-10-05T00:00:00Z',retrieved_at:'2026-10-06T00:00:00Z',first_seen_at:'2026-10-06T00:00:00Z',tickers:['AAPL'],evidence_meta:{tag:'NetIncomeLoss',value:120,start:'2026-07-01',end:'2026-09-30'},research:{takeaway:'Profit improved, but cash conversion needs checking.',mechanism:'Recurring profit can support operating flexibility.',next_step:'Compare cash flow.',facts:[{text:'<img src=x onerror=steal()>',url:'javascript:alert(1)'}],bull:['If cash backs the improvement.'],bear:['One-off gains may reverse.'],ranking:{score:50,eligible_weekly:true,components:{source_support:20,missing_expectations:-10}},calculations:[]}};
const payload={events:[event],status:[{updated_at:'2026-10-06T00:00:00Z',payload:{jobs:[],cadence:'daily_scheduled'}}],weekly:[event.id],financial_context:{AAPL:[]},source_health:[{id:'wsj',name:'Wall Street Journal',integration_status:'licensed access required',records:0,errors:[],documentation_url:'https://www.wsj.com'}]};
const calls=[];
const sandbox={document,window,URL,Date,console,setTimeout,fetch:async(path,options)=>{calls.push({path,options});let d=path==='/api/dashboard'?payload:path==='/api/session'?{user:null}:{watchlist:[]};if(options&&path==='/api/session')return{ok:false,json:async()=>({error:'Sign in'})};return{ok:true,json:async()=>d};}};
vm.runInNewContext(readFileSync(new URL('../public/app.js',import.meta.url),'utf8'),sandbox);
await new Promise(resolve=>setTimeout(resolve,30));
assert.match(document.querySelector('#board').textContent,/Profit improved/);
assert.match(document.querySelector('#board').textContent,/Why it matters/);
assert.equal(document.querySelector('#board img'),null);
assert.equal(document.querySelector('[href^="javascript:"]'),null);
for(const view of ['opportunities','watchlist','macro','history','sources','brief']){
 document.querySelector(`[data-view="${view}"]`).dispatchEvent(new window.Event('click'));
 assert.ok(document.querySelector('#view-heading').textContent.length>0);
}
document.querySelector('[data-view="sources"]').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#board').textContent,/licensed access required/);
document.querySelector('[data-view="brief"]').dispatchEvent(new window.Event('click'));
document.querySelector('.symbols button').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#company').textContent,/AAPL.*Research dossier/);
assert.match(document.querySelector('#company').textContent,/Price-history statistics are unavailable/);
document.querySelector('#collect').dispatchEvent(new window.Event('click'));
assert.match(document.querySelector('#auth-message').textContent,/Sign in/);
assert.ok(!calls.some(c=>c.path==='/api/collect'));
console.log('UI smoke passed: navigation, company dossier, missing-data states, unsafe-content handling and authenticated collection gate');
