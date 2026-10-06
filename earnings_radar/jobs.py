"""Persistent single-owner jobs with expired-lease recovery and bounded retries."""
import time
from earnings_radar.db import utc_now

LEASE_SECONDS=120

def seed(conn,names):
    for name in names: conn.execute('INSERT OR IGNORE INTO jobs(name) VALUES (?)',(name,))

def claim(conn,owner,*,now=None):
    now=time.time() if now is None else now
    conn.execute('BEGIN IMMEDIATE')
    row=conn.execute("SELECT * FROM jobs WHERE next_run<=? AND lease_until<=? AND status!='disabled' ORDER BY next_run,name LIMIT 1",(now,now)).fetchone()
    if not row: conn.commit();return None
    conn.execute("UPDATE jobs SET lease_owner=?,lease_until=?,status='running' WHERE name=?",(owner,now+LEASE_SECONDS,row['name']))
    conn.commit()
    return dict(row)

def finish(conn,name,owner,*,checkpoint=None,error=None,interval=300,now=None,max_attempts=5):
    now=time.time() if now is None else now
    row=conn.execute('SELECT * FROM jobs WHERE name=? AND lease_owner=? AND lease_until>?',(name,owner,now)).fetchone()
    if not row: raise RuntimeError('job lease lost; discard results')
    failures=row['failures']+1 if error else 0
    delay=min(3600,30*2**min(failures,7)) if error else interval
    if failures>=max_attempts: delay=3600  # Pause then probe again; no tight retry loop.
    conn.execute('UPDATE jobs SET lease_owner=NULL,lease_until=0,status=?,failures=?,next_run=?,checkpoint=?,last_success=?,last_error=? WHERE name=? AND lease_owner=?',('degraded' if error else 'healthy',failures,now+delay,row['checkpoint'] if error else checkpoint,row['last_success'] if error else utc_now(),error,name,owner))

def verify_lease(conn,name,owner):
    row=conn.execute('SELECT 1 FROM jobs WHERE name=? AND lease_owner=? AND lease_until>?',(name,owner,time.time())).fetchone()
    if not row: raise RuntimeError('job lease lost')
