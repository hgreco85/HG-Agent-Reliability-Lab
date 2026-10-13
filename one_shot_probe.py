"""One-time production smoke probe. Never prints credentials or retries."""
import json
import os
import urllib.request
import urllib.error

def main():
    if os.getenv("VERCEL_ENV") != "production":
        print("HG_NEMOTRON_PROBE: SKIP_NON_PRODUCTION")
        return
    token = os.getenv("HG_DEMO_ACCESS_TOKEN")
    if not token or os.getenv("HG_NEBIUS_LIVE_ENABLED") != "YES":
        print("HG_NEMOTRON_PROBE: SKIP_NOT_ENABLED")
        return
    url = "https://hg-agent-reliability-lab-nebius.vercel.app/api/revocation"
    req = urllib.request.Request(
        url, data=b"", method="POST",
        headers={"X-Demo-Token": token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=42) as response:
            status = response.status
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            result = json.load(exc)
        except (ValueError, OSError):
            result = {}
    except (TimeoutError, urllib.error.URLError, OSError):
        print("HG_NEMOTRON_PROBE: NETWORK_UNAVAILABLE; NO_RETRY")
        return
    assessment = result.get("result") or {}
    print("HG_NEMOTRON_PROBE:", json.dumps({
        "http": status,
        "status": result.get("status"),
        "live_api": result.get("live_api") is True,
        "source": result.get("source"),
        "decision": assessment.get("decision_normalized"),
        "pass": assessment.get("pass"),
        "usage": result.get("usage", {}),
    }, sort_keys=True))

if __name__ == "__main__":
    main()
