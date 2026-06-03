#!/usr/bin/env python3
"""Tiny local proxy: fetches SPK.NZ price from Yahoo Finance, serves it on localhost:7654."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, json

URL = 'https://query1.finance.yahoo.com/v8/finance/chart/SPK.NZ?interval=1d&range=1d'
HEADERS = {'User-Agent': 'Mozilla/5.0'}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            req = urllib.request.Request(URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
        except Exception as e:
            data = json.dumps({'error': str(e)}).encode()
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # silence request logs

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 7654), Handler)
    print('SPK proxy running on http://localhost:7654 — Ctrl+C to stop')
    server.serve_forever()
