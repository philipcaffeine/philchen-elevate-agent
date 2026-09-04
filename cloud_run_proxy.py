#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import time
import urllib.request
import urllib.error

TARGET_URL = 'https://altostrat-hr-agent-1086030028624.asia-southeast1.run.app'
PORT = 8085

cached_token = None
token_expiry = 0

def get_token():
    global cached_token, token_expiry
    now = time.time()
    if not cached_token or now >= token_expiry:
        token = subprocess.check_output(['gcloud', 'auth', 'print-identity-token']).decode().strip()
        cached_token = token
        token_expiry = now + 1800
    return cached_token

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.proxy_request('GET')

    def do_POST(self):
        self.proxy_request('POST')

    def do_PUT(self):
        self.proxy_request('PUT')

    def do_DELETE(self):
        self.proxy_request('DELETE')

    def do_HEAD(self):
        self.proxy_request('HEAD')

    def proxy_request(self, method):
        target = f'{TARGET_URL}{self.path}'
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ('host', 'authorization')}
        try:
            token = get_token()
            headers['Authorization'] = f'Bearer {token}'
        except Exception as e:
            self.send_error(500, f'Token error: {e}')
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        req = urllib.request.Request(target, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ('transfer-encoding', 'content-length'):
                        self.send_header(k, v)
                resp_body = resp.read()
                self.send_header('Content-Length', str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ('transfer-encoding', 'content-length'):
                    self.send_header(k, v)
            resp_body = e.read()
            self.send_header('Content-Length', str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as e:
            self.send_error(502, f'Proxy error: {e}')

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(('0.0.0.0', PORT), ProxyHandler) as httpd:
        print(f'Proxy serving on 0.0.0.0:{PORT} -> {TARGET_URL}')
        httpd.serve_forever()
