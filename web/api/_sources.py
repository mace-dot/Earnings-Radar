"""Readable primary-source destinations; raw structured data remains optional."""
import re
from urllib.parse import urlsplit
LABELS={'RevenueFromContractWithCustomerExcludingAssessedTax':'Revenue','NetIncomeLoss':'Net profit / loss','GrossProfit':'Gross profit','OperatingIncomeLoss':'Operating profit / loss','NetCashProvidedByUsedInOperatingActivities':'Operating cash flow','PaymentsToAcquirePropertyPlantAndEquipment':'Capital expenditure','Assets':'Total assets','Liabilities':'Total liabilities','InterestExpense':'Interest expense'}

LABELS.update({'Revenues': 'Revenue', 'SalesRevenueNet': 'Revenue', 'AssetsCurrent': 'Short-term assets', 'LiabilitiesCurrent': 'Short-term obligations', 'CashAndCashEquivalentsAtCarryingValue': 'Cash and cash equivalents', 'LongTermDebtCurrent': 'Long-term debt due within a year', 'LongTermDebtNoncurrent': 'Long-term debt due later', 'ShortTermBorrowings': 'Short-term borrowings', 'StockBasedCompensation': 'Stock-based compensation', 'CommonStockSharesOutstanding': 'Common shares outstanding', 'StockholdersEquity': 'Shareholders’ equity'})

def readable(e):
 m=e.get('evidence_meta',{});url=e['url'];out=dict(e)
 if e['provider']=='sec_fundamentals':
  match=re.search(r'/CIK(\d{10})/',url);acc=m.get('accession','');symbol=next(iter(e.get('tickers',[])),'Company')
  if match and re.fullmatch(r'\d{10}-\d{2}-\d{6}',acc):url=f'https://www.sec.gov/Archives/edgar/data/{int(match[1])}/{acc.replace("-","")}/{acc}-index.htm'
  out['display_title']=f"{symbol} · {LABELS.get(m.get('tag'), 'Reported financial figure')} · period ended {m.get('end','unknown')}"
  out['display_value']=f"{'$' if m.get('units','USD')=='USD' else ''}{m['value']:,.0f}{' shares' if m.get('units')=='shares' else ''}" if isinstance(m.get('value'),(int,float)) else 'Figure unavailable'
 else:out['display_title']=e['title']
 out['readable_url']=url;out['source_label']='Read the financial filing' if e['provider']=='sec_fundamentals' else 'Read original source'
 return out
