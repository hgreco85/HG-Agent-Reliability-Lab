# HG Agent Reliability Lab

Evidence-first AI-agent reliability prototype, built for the **Nebius × NVIDIA Global AI Hackathon 2026**.

**[Interactive demo](https://hg-agent-reliability-lab-nebius.vercel.app)** · **[Video demonstration](https://youtu.be/44dX_pD3OMo)**

## What it does

A small, independent browser demo and Python scorer show how to audit an agent's behavior when tools fail, a document cannot be retrieved, or cached information is unverified. The public demo includes a five-case, browser-based reliability evaluation (safe and unsafe strategies), with per-case explanations and an independent Python evaluator. These are **deterministic synthetic tests**, not agent inference or model benchmark results.

## Usage

Open `index.html` directly in a browser. Offline scoring requires Python 3:

```sh
python evaluator.py
python -m unittest test_evaluator.py test_demo_contract.py -v
```

No third-party packages or API key are required to run the public demo and scorer. The five UI scenarios match the scorer's case IDs, tool states, verification flags and expected actions, enforced by CI.\n\n### What judges can verify\n\n1. Open the demo and run **Evaluate safe policy (5 cases)** to see a deterministic 5/5 with case-level explanations.\n2. Run **Evaluate unsafe policy (5 cases)** to see explicit rejection of fabrication and unverified cache usage.\n3. Run the above Python tests offline to verify consistency and fail-closed scoring.\n4. Inspect `/api/revocation` read-only status; real inference is intentionally disabled after the previous single-use attempt.\n\n**Evidence boundary:** Passing the synthetic policy does not establish broad Nemotron reliability. One real Nebius Token Factory/Nemotron inference on 2026-10-26 reportedly returned the expected `ask_for_source` action for a single synthetic failure scenario. See [sanitized receipt](reports/nebius_one_shot_20261026_sanitized.md). Actual final metered cost is not yet verified.

## Authenticated NVIDIA Nemotron evidence

Nemotron 3 Nano 30B A3B was queried through Nebius Token Factory in isolated GitHub Actions executions:

- Connectivity: 70 tokens, `READY`, successful API response.
- Recovery assessment: 450 tokens, no visible content after reaching 256-token output budget; functional recovery **not demonstrated**.

A later one-shot real test returned `ask_for_source` on a synthetic tool failure. The [sanitized evidence file](reports/nebius_one_shot_20261026_sanitized.md) links its original workflow run and reports 316 tokens. Private workflow logs may not be readable by judges; this public receipt does not contain credentials. It proves one reported successful case, **not** a broad live recovery benchmark or real local fallback. Final Nebius billing remains unverified.

## Scope and security

This standalone public repository excludes private HG Market System code, credentials, tokens, deployment configuration and trading systems. The five-case public simulation is static: loading the site or pressing simulation controls makes no model API calls. A separately authenticated live inference button exists but its server execution is currently disabled.

Licensed MIT. Copyright © 2026 HG Stack.
