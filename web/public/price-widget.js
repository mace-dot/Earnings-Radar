'use strict';
// Provider-hosted website widget: no scraping, API credential or raw-price proxy.
function marketChartSymbol(company){
 const symbol=company?.symbol;
 if(typeof symbol!=='string'||! /^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(symbol))throw new Error('Invalid chart symbol');
 const exchanges={NASDAQ:'NASDAQ',NYSE:'NYSE','NYSE AMERICAN':'AMEX',AMEX:'AMEX','NYSE ARCA':'AMEX',ARCA:'AMEX',BATS:'BATS',CBOE:'BATS',OTC:'OTC'};
 const exchange=exchanges[String(company.exchange||'').toUpperCase()];
 // Class-share separators differ between SEC and the widget provider.
 const ticker=symbol.replaceAll('-','.');return exchange?`${exchange}:${ticker}`:ticker;
}
function mountMarketChart(root,company){
 const symbol=marketChartSymbol(company),box=document.createElement('section');box.className='market-chart';
 const h=document.createElement('h3');h.textContent=`${company.symbol} · Price action`;box.append(h);
 const p=document.createElement('p');p.textContent='Interactive price chart supplied by TradingView. Check its quote timestamp and live/delayed indicator; market closures and exchange delays still apply.';box.append(p);
 const frame=document.createElement('iframe');
 const params=new URLSearchParams({symbol,interval:'1',theme:'dark',style:'1',timezone:'America/New_York',withdateranges:'1',hide_side_toolbar:'0',allow_symbol_change:'0',save_image:'0',locale:'en'});
 frame.src='https://s.tradingview.com/widgetembed/?'+params.toString();frame.title=`${company.symbol} interactive price chart from TradingView`;frame.className='market-chart-frame';frame.setAttribute('loading','eager');frame.setAttribute('referrerpolicy','strict-origin-when-cross-origin');frame.setAttribute('allowfullscreen','');box.append(frame);
 const credit=document.createElement('a');credit.href='https://www.tradingview.com/chart/?symbol='+encodeURIComponent(symbol);credit.target='_blank';credit.rel='noopener noreferrer';credit.textContent=`${company.symbol} chart by TradingView · Open full chart`;box.append(credit);
 const help=document.createElement('p');help.className='small-copy';help.textContent='Use the chart’s interval and date-range controls to explore intraday movement and price history. If the embedded chart is blocked by your browser, open the full chart above.';box.append(help);
 root.append(box);return box;
}
