"""Database operation CLI. Stop worker and UI before restoring."""
import argparse
from pathlib import Path
import os
import sqlite3
from earnings_radar.migrations import backup
from earnings_radar.db import init_db
from earnings_radar.sources import research_path

def restore(source,target,*,services_stopped=False):
    if not services_stopped:raise ValueError('stop worker/UI and confirm --services-stopped before restore')
    source=Path(source);target=Path(target)
    if source.resolve()==target.resolve():raise ValueError('restore source and target must differ')
    if not source.is_file():raise FileNotFoundError(source)
    with sqlite3.connect(f'file:{source.resolve()}?mode=ro',uri=True) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('restore source failed integrity check')
        required={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'earnings_events','option_quotes','research_notes','paper_trades'}<=required:raise ValueError('not an Earnings Radar database')
    preserved=backup(target) if target.exists() else None
    staging=target.with_name(target.name+'.restore-pending')
    backup(source,staging)
    # Explicitly stopped processes are required: old WAL must not replay into restored DB.
    for suffix in ('-wal','-shm'):
        Path(str(target)+suffix).unlink(missing_ok=True)
    os.replace(staging,target)
    return preserved

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=['migrate','backup','restore'])
    parser.add_argument('--db',type=Path,default=research_path())
    parser.add_argument('--source',type=Path)
    parser.add_argument('--services-stopped',action='store_true')
    args=parser.parse_args()
    if args.operation=='migrate':print(init_db(args.db))
    elif args.operation=='backup':print(backup(args.db))
    else:
        if args.source is None:parser.error('--source required')
        print('Prior target backup:',restore(args.source,args.db,services_stopped=args.services_stopped))

if __name__=='__main__':main()
