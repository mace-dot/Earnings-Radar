"""Evaluate a supplied point-in-time JSON dataset; never enable or deploy a model."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from web.api._validation import walk_forward
p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if a.dataset.stat().st_size>5_000_000:raise SystemExit('Dataset exceeds the bounded offline evaluation size')
rows=json.loads(a.dataset.read_text())
if not isinstance(rows,list):raise SystemExit('Provide a JSON observation list')
report=walk_forward(rows)
a.output.write_text(json.dumps(report,indent=2)+'\n')
print('Offline report written. No live model has been promoted.')
