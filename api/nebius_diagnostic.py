"""Read-only one-attempt Nebius credential/catalog check. No inference calls."""
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

CHECK_KEY = "hg-agent-reliability-lab:nebius:model-catalog-check:v2:corrected-key:spent"
CATALOG = "https://api.tokenfactory.nebius.com/v1/models"
EXPECTED = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"

def reserve():
    base = os.getenv("KV_REST_API_URL", "")
    token = os.getenv("KV_REST_API_TOKEN", "")
    if not base.startswith("https://") or not token:
        return False
    request = urllib.request.Request(
        base.rstrip("/"), data=json.dumps(["SET", CHECK_KEY, "spent", "NX"]).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
            return result.get("result") == "OK" and not result.get("error")
    except (TimeoutError, urllib.error.URLError, ValueError, OSError):
        return False

def inspect_once():
    if os.getenv("VERCEL_ENV") != "production" or os.getenv("HG_CATALOG_CHECK_ENABLED") != "YES":
        return {"status": "DISABLED"}, 503
    key = os.getenv("NEBIUS_API_KEY", "")
    if not key:
        return {"status": "MISSING_SECRET"}, 503
    if not reserve():
        return {"status": "ALREADY_CHECKED_OR_GATE_UNAVAILABLE"}, 409
    if "*" in key or key != key.strip():
        return {"status": "INVALID_KEY_FORMAT", "suspected_masked_or_whitespace": True}, 422
    req = urllib.request.Request(CATALOG, headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            raw = json.load(response)
            models = raw.get("data", [])
            ids = [v.get("id") for v in models if isinstance(v, dict)]
            return {"status": "CATALOG_OK", "upstream_http": response.status,
                    "model_available": EXPECTED in ids,
                    "models_returned": len(ids)}, 200
    except urllib.error.HTTPError as err:
        return {"status": "CATALOG_HTTP_ERROR", "upstream_http": err.code}, 502
    except (TimeoutError, urllib.error.URLError, ValueError, OSError):
        return {"status": "CATALOG_UNAVAILABLE"}, 502

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        value, status = inspect_once()
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
