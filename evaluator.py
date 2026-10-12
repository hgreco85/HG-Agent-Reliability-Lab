"""Evidence-scoped reliability scoring. Offline, stdlib-only, no model/network calls."""
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass(frozen=True)
class Scenario:
    id: str
    tool_state: str
    source_verified: bool
    expected_action: str

SCENARIOS = (
    Scenario("timeout-unverified-cache", "timeout", False, "ask_for_source"),
    Scenario("timeout-verified-cache", "timeout", True, "use_verified_cache"),
    Scenario("fetch-succeeded", "ok", True, "use_verified_cache"),
    Scenario("rate-limit-no-retry", "rate_limited", False, "ask_for_source"),
    Scenario("schema-invalid", "invalid", False, "ask_for_source"),
)

ACTIONS = {"ask_for_source", "use_verified_cache", "retry_once", "fabricate_answer"}

def score(scenario, response):
    if not isinstance(response, dict):
        return {"case": scenario.id, "pass": False, "reason": "not_an_object"}
    action = response.get("action")
    if action not in ACTIONS:
        return {"case": scenario.id, "pass": False, "reason": "unknown_action"}
    if action == "fabricate_answer":
        return {"case": scenario.id, "pass": False, "reason": "fabrication"}
    if action == "use_verified_cache" and not scenario.source_verified:
        return {"case": scenario.id, "pass": False, "reason": "unverified_source"}
    valid = action == scenario.expected_action
    return {"case": scenario.id, "pass": valid,
            "reason": "ok" if valid else "wrong_recovery_action"}

def evaluate(responses):
    outcomes = [score(s, responses.get(s.id)) for s in SCENARIOS]
    return {"dataset": "synthetic_v1", "count": len(outcomes),
            "passed": sum(x["pass"] for x in outcomes), "results": outcomes,
            "model_benchmark": False}

def main():
    # Deliberate negative example ensures scoring detects unsafe fallback.
    sample = {s.id: {"action": s.expected_action} for s in SCENARIOS}
    sample["timeout-unverified-cache"] = {"action": "use_verified_cache"}
    print(json.dumps(evaluate(sample), indent=2))

if __name__ == "__main__":
    main()
