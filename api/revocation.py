"""Vercel Python function: authenticated, one-shot Nemotron revocation demo."""
from http.server import BaseHTTPRequestHandler
import hmac
import json
import os
import urllib.error
from nebius_revocation import ENDPOINT, request_payload, evaluate
import urllib.request

class handler(BaseHTTPRequestHandler):
    def reply(self, code, data):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.reply(200, {"status": "READY" if os.getenv("NEBIUS_API_KEY") and os.getenv("HG_DEMO_ACCESS_TOKEN") else "UNCONFIGURED",
                         "mode": "REAL_API", "model": "NVIDIA-Nemotron-3-Nano-30B-A3B",
                         "authentication": "required"})

    def do_POST(self):
        access_token = os.getenv("HG_DEMO_ACCESS_TOKEN", "")
        neb_key = os.getenv("NEBIUS_API_KEY", "")
        if not access_token or not neb_key:
            self.reply(503, {"status": "UNCONFIGURED", "live_api": False})
            return
        actual = self.headers.get("X-Demo-Token", "")
        if not actual or not hmac.compare_digest(actual, access_token):
            self.reply(403, {"status": "FORBIDDEN", "live_api": False})
            return
        if self.headers.get("Content-Length", "0") != "0":
            self.reply(400, {"status": "FIXED_SCENARIO_ONLY"})
            return
        req = urllib.request.Request(ENDPOINT,
            data=json.dumps(request_payload()).encode(),
            headers={"Authorization":"Bearer "+neb_key,"Content-Type":"application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=35) as res:
                raw = json.load(res)
        except urllib.error.HTTPError as err:
            self.reply(502, {"status":"MODEL_HTTP_ERROR","upstream_status":err.code})
            return
        except (TimeoutError, urllib.error.URLError, ValueError) as err:
            self.reply(502, {"status":"MODEL_UNAVAILABLE"})
            return
        assessment = evaluate(raw)
        self.reply(200 if assessment.get("pass") else 422,
                   {"status":"PASS" if assessment.get("pass") else "FAIL",
                    "live_api":True, "source":"NEBIUS_TOKEN_FACTORY",
                    "result":assessment,"usage":raw.get("usage",{})})
