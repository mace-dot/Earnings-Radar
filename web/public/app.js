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
    events = data.events || []; const status = data.status?.[0]; coverage = status?.payload?.sources || []; tracked = status?.payload?.watchlist || ['AAPL','MSFT','NVDA']; quant = status?.payload?.quantitative || {}; fundamentals = status?.payload?.fundamentals || {}; renderWatchlist();
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

let tracked = ['AAPL','MSFT','NVDA'], quant = {}, fundamentals = {}, selectedStock = null;
let extra = [];
try { extra = JSON.parse(localStorage.getItem('radar-watchlist') || '[]').filter(s => typeof s === 'string' && /^[A-Z][A-Z0-9.-]{0,9}$/.test(s)).slice(0,20); } catch { extra = []; }
function metric(parent, label, value, suffix = '', scale = 1) {
  const n = el('div', label); n.append(el('strong', typeof value === 'number' && Number.isFinite(value) ? (value*scale).toFixed(2)+suffix : 'Unavailable')); parent.append(n);
}
function renderWatchlist() {
  const root = document.querySelector('#watchlist'); root.replaceChildren();
  for (const symbol of [...new Set([...tracked, ...extra])]) {
    const q = quant[symbol] || {}, n = el('article', undefined, 'card'); n.append(el('h2', symbol));
    const count = events.filter(e => e.tickers.includes(symbol)).length;
    n.append(el('p', `${count} collected source records · ${tracked.includes(symbol) ? 'Collector watchlist' : 'Browser watchlist; automatic collection not configured'}`));
    if (q.status === 'available') {
      n.append(el('p', `Daily-bar statistics as of ${q.as_of_session} · IEX coverage`));
      const grid = el('div', undefined, 'metric-grid');
      metric(grid, '20-session annualized volatility', q.realized_volatility_20, '%', 100);
      metric(grid, '60-session annualized volatility', q.realized_volatility_60, '%', 100);
      metric(grid, 'Latest return z-score', q.latest_return_zscore);
      metric(grid, 'Average true range / price', q.atr_percent_14, '%', 100);
      metric(grid, '20-session momentum', q.momentum_20, '%', 100);
      metric(grid, 'Drawdown from 60-session high', q.drawdown_60, '%', 100);
      metric(grid, '60-session beta vs SPY', q.beta_60);
      n.append(grid); list(n, 'Research flags', q.flags); n.append(el('p', q.interpretation));
    } else n.append(el('p', q.status === 'insufficient_history' ? `Need 61 daily bars; ${q.available_bars} available.` : 'Quantitative signals unavailable: historical market data is not connected or has not been collected.'));
    const facts = fundamentals[symbol] || [];
    for (const f of facts) { n.append(el('p', `${f.metric}: ${Number(f.reported_value_usd).toLocaleString()} USD · period ended ${f.period_end} · ${typeof f.year_over_year_pct === 'number' ? f.year_over_year_pct.toFixed(2)+'% year-over-year' : 'Comparable prior year unavailable'}`)); }
    n.append(el('p', 'Consensus gap: unverified. A contrarian thesis needs documented market expectations, comparable results, a catalyst, and counterevidence.'));
    const actions = el('div', undefined, 'watch-actions'), view = el('button', selectedStock === symbol ? 'Show all companies' : 'View company research');
    view.addEventListener('click', () => { selectedStock = selectedStock === symbol ? null : symbol; document.querySelector('#search').value = selectedStock || ''; filter = 'all'; document.querySelectorAll('[data-filter]').forEach(b => b.classList.toggle('active',b.dataset.filter === 'all')); render(); renderWatchlist(); }); actions.append(view);
    if (!tracked.includes(symbol)) { const remove = el('button', 'Remove'); remove.addEventListener('click', () => { extra = extra.filter(s => s !== symbol); saveWatchlist(); renderWatchlist(); }); actions.append(remove); }
    n.append(actions); root.append(n);
  }
}
function saveWatchlist() { try { localStorage.setItem('radar-watchlist', JSON.stringify(extra)); } catch { document.querySelector('#watchlist-message').textContent = 'Browser storage is unavailable; changes apply to this visit only.'; } }
document.querySelector('#watchlist-form').addEventListener('submit', e => {
  e.preventDefault(); const input = document.querySelector('#watchlist-symbol'), s = input.value.trim().toUpperCase();
  if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(s)) { document.querySelector('#watchlist-message').textContent = 'Enter a valid ticker symbol.'; return; }
  if (extra.length >= 20) { document.querySelector('#watchlist-message').textContent = 'Browser watchlist limit: 20 extra stocks.'; return; }
  if (!tracked.includes(s) && !extra.includes(s)) extra.push(s); saveWatchlist(); input.value = ''; renderWatchlist();
  document.querySelector('#watchlist-message').textContent = `${s} added. Browser additions filter existing research; they do not enable new backend collection. The collector watchlist is configured separately.`;
});
renderWatchlist();
