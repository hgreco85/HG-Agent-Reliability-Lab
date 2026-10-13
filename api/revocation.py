"""Fail-closed Nemotron endpoint: atomic, persistent one-shot Redis gate."""
from http.server import BaseHTTPRequestHandler
import hmac, json, os, urllib.request, urllib.error
from nebius_revocation import ENDPOINT, request_payload, evaluate

GATE_KEY = "hg-agent-reliability-lab:nebius:revocation:v1:spent"

def ready():
    required = ("NEBIUS_API_KEY", "HG_DEMO_ACCESS_TOKEN",
                "KV_REST_API_URL", "KV_REST_API_TOKEN")
    key = os.getenv("NEBIUS_API_KEY", "")
    # Never forward a masked/copy-pasted credential or whitespace to the provider.
    if not key or "*" in key or key != key.strip():
        return False
    return os.getenv("HG_NEBIUS_LIVE_ENABLED") == "YES" and all(os.getenv(k) for k in required)

def claim_once():
    """Atomic SET NX without expiration. Never undo a reservation or retry."""
    url = os.environ["KV_REST_API_URL"].rstrip("/")
    if not url.startswith("https://"):
        return False
    req = urllib.request.Request(
        url, data=json.dumps(["SET", GATE_KEY, "spent", "NX"]).encode(),
        headers={"Authorization": "Bearer " + os.environ["KV_REST_API_TOKEN"],
                 "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.load(response)
            return isinstance(payload, dict) and payload.get("result") == "OK" and not payload.get("error")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False

def gate_status():
    """Read-only status from Redis. No Nebius request, no SET, no resets."""
    url = os.getenv("KV_REST_API_URL", "").rstrip("/")
    token = os.getenv("KV_REST_API_READ_ONLY_TOKEN", "")
    if not url.startswith("https://") or not token:
        return "UNKNOWN"
    req = urllib.request.Request(
        url, data=json.dumps(["GET", GATE_KEY]).encode(),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.load(response)
            if not isinstance(payload, dict) or payload.get("error"):
                return "UNKNOWN"
            return "SPENT" if payload.get("result") == "spent" else (
                "UNUSED" if payload.get("result") is None else "UNKNOWN")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return "UNKNOWN"

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
        self.reply(200, {"status": "READY" if ready() else "DISABLED",
                         "model": "NVIDIA-Nemotron-3-Nano-30B-A3B",
                         "authentication": "required", "max_live_calls_per_gate": 1,
                         "gate_status": gate_status()})

    def do_POST(self):
        if not ready():
            self.reply(503, {"status": "DISABLED", "live_api": False})
            return
        actual = self.headers.get("X-Demo-Token", "")
        if not actual or not hmac.compare_digest(actual, os.environ["HG_DEMO_ACCESS_TOKEN"]):
            self.reply(403, {"status": "FORBIDDEN", "live_api": False})
            return
        if self.headers.get("Content-Length", "0") != "0" or self.headers.get("Transfer-Encoding"):
            self.reply(400, {"status": "FIXED_SCENARIO_ONLY", "live_api": False})
            return
        if not claim_once():
            self.reply(409, {"status": "ALREADY_USED_OR_GATE_UNAVAILABLE", "live_api": False})
            return
        payload = request_payload()
        payload["max_tokens"] = 256
        req = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + os.environ["NEBIUS_API_KEY"],
                     "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=35) as res:
                raw = json.load(res)
        except urllib.error.HTTPError as err:
            self.reply(502, {"status": "MODEL_HTTP_ERROR", "upstream_status": err.code, "live_api": False})
            return
        except (TimeoutError, urllib.error.URLError, ValueError, OSError):
            self.reply(502, {"status": "MODEL_UNAVAILABLE", "live_api": False})
            return
        assessment = evaluate(raw)
        self.reply(200 if assessment.get("pass") else 422,
                   {"status": "PASS" if assessment.get("pass") else "FAIL",
                    "live_api": True, "source": "NEBIUS_TOKEN_FACTORY",
                    "result": assessment, "usage": raw.get("usage", {})})
