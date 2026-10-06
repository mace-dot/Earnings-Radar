"""Read-only public dashboard API. No client-selected SQL or write endpoints."""
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler
sys.path.insert(0, str(Path(__file__).parent))
from _store import Store, StoreError

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            payload = Store().dashboard()
            status = 200
        except StoreError as exc:
            payload = {'error': str(exc), 'events': [], 'status': []}
            status = 503
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'public, max-age=60' if status == 200 else 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)
