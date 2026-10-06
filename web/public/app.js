'use strict';
let events = [], filter = 'all', coverage = [];
const el = (tag, value, cls) => { const n = document.createElement(tag); if (value !== undefined) n.textContent = value; if (cls) n.className = cls; return n; };
function link(url, label) {
  const n = el('a', label);
  try { const u = new URL(url); if (u.protocol !== 'https:' || u.username || u.password) return el('span', label); n.href = u.href; } catch { return el('span', label); }
  n.target = '_blank'; n.rel = 'noopener noreferrer'; return n;
}
function date(s) { const d = new Date(s); return Number.isNaN(d.valueOf()) ? 'Unknown date' : d.toLocaleString(); }
function list(parent, title, values) {
  parent.append(el('h3', title, 'label'));
  if (!values?.length) { parent.append(el('p', 'Not established from available evidence.')); return; }
  const ul = el('ul'); for (const v of values) ul.append(el('li', v)); parent.append(ul);
}
function render() {
  const board = document.querySelector('#board'), sources = document.querySelector('#sources');
  board.replaceChildren(); sources.replaceChildren(); sources.hidden = filter !== 'sources'; board.hidden = filter === 'sources';
  if (filter === 'sources') {
    for (const s of coverage) { const n = el('article', undefined, 'source'); n.append(el('h2', s.name), el('p', s.access_status.replaceAll('_',' ')), el('p', s.capabilities), link(s.documentation_url, 'Provider information')); sources.append(n); }
    if (!coverage.length) sources.append(el('p', 'Source coverage will appear after the collector runs.'));
    return;
  }
  const q = document.querySelector('#search').value.trim().toLowerCase();
  const shown = events.filter(e => (filter === 'all' || e.analysis?.category === filter) && `${e.title} ${e.tickers.join(' ')}`.toLowerCase().includes(q));
  for (const e of shown) {
    const a = e.analysis || {}, n = el('article', undefined, 'card'), top = el('div', undefined, 'top');
    top.append(el('span', e.institution || e.provider), el('span', (a.suggested_action || 'investigate').toUpperCase(), 'badge'));
    n.append(top, el('h2', e.title), el('div', e.tickers.join(' · ') || 'MACRO / POLICY', 'symbols'));
    n.append(el('p', `Published ${date(e.published_at)} · Last retrieved ${date(e.retrieved_at)}`));
    n.append(el('p', `Source support: ${a.evidence_confidence || 'unknown'} · Historical / backfilled research`));
    n.append(el('p', a.economic_mechanism || 'Read the primary source before drawing conclusions.'), link(e.url, 'Read original source ↗'));
    const d = el('details'); d.append(el('summary', 'Facts, thesis checks & missing information'));
    list(d, 'Confirmed source facts', (a.confirmed_facts || []).map(f => f.excerpt));
    list(d, 'Bullish implications', a.bullish_implications); list(d, 'Bearish implications', a.bearish_implications);
    list(d, 'Counterevidence', a.counterevidence); list(d, 'What would invalidate this', a.invalidation_conditions); list(d, 'Still needed', a.missing_information);
    d.append(el('p', a.observed_reaction || 'Market reaction is not verified.'), el('p', a.caveat || 'Evidence confidence is not a trading-success probability.')); n.append(d); board.append(n);
  }
  if (!shown.length) board.append(el('div', events.length ? 'No research matches this filter.' : 'No research collected yet. Configure the Supabase database and run the GitHub collector to populate this board.', 'empty'));
}
async function load() {
  const button = document.querySelector('#refresh'); button.disabled = true;
  try {
    const r = await fetch('/api/dashboard'); const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Unable to load research');
    events = data.events || []; const status = data.status?.[0]; coverage = status?.payload?.sources || [];
    document.querySelector('#count').textContent = String(events.length);
    const age = status ? (Date.now() - new Date(status.updated_at).valueOf()) / 3600000 : Infinity;
    document.querySelector('#freshness').textContent = status ? `${age > 2 ? 'STALE · ' : ''}Last collection ${date(status.updated_at)} · hourly schedule, timing may vary` : 'Database connected · awaiting first collection';
    const failures = status?.payload?.jobs?.filter(j => j.last_error) || [];
    document.querySelector('#notice').textContent = failures.length ? `Some sources are unavailable: ${failures.map(j => j.name).join(', ')}. See Source coverage for access requirements.` : '';
  } catch (e) {
    document.querySelector('#notice').textContent = e.message || 'Unable to connect to the research database.';
    document.querySelector('#freshness').textContent = 'Data connection unavailable';
  } finally { render(); button.disabled = false; }
}
document.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => { filter = b.dataset.filter; document.querySelectorAll('[data-filter]').forEach(x => x.classList.toggle('active', x === b)); render(); }));
document.querySelector('#search').addEventListener('input', render); document.querySelector('#refresh').addEventListener('click', load); load();
