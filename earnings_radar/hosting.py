"""Run the UI and collector together on one persistent host; fail on either crash."""
import os
import signal
import subprocess
import sys
import time
from earnings_radar.sources import prepare
from earnings_radar.db import init_db
from earnings_radar.config import DB_PATH,ROOT_DIR


def main():
    if not os.environ.get('RADAR_DASHBOARD_PASSWORD'):
        raise SystemExit('Set RADAR_DASHBOARD_PASSWORD securely before hosted startup.')
    os.environ['RADAR_REQUIRE_AUTH']='true'
    port=int(os.getenv('PORT','8501'))
    if not 1<=port<=65535:raise SystemExit('Invalid PORT')
    init_db(DB_PATH);prepare()
    commands=[
        [sys.executable,'-m','earnings_radar.worker'],
        [sys.executable,'-m','streamlit','run',str(ROOT_DIR/'app.py'),'--server.headless=true','--server.address=0.0.0.0',f'--server.port={port}','--browser.gatherUsageStats=false']
    ]
    children=[];stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
        for child in children:
            if child.poll() is None:child.terminate()
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
    try:
        for command in commands:children.append(subprocess.Popen(command,cwd=ROOT_DIR))
        while not stopping:
            failed=next((child for child in children if child.poll() is not None),None)
            if failed is not None:
                raise RuntimeError('A hosted component exited; restart the service.')
            time.sleep(.5)
    finally:
        stop()
        for child in children:
            try:child.wait(timeout=30)
            except subprocess.TimeoutExpired:child.kill();child.wait()

if __name__=='__main__':main()
