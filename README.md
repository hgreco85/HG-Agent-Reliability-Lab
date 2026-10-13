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

No third-party packages or API key are required to run the public demo and scorer. The five UI scenarios match the scorer's case IDs, tool states, verification flags and expected actions, enforced by CI.\n\n### What judges can verify\n\n1. Open the demo and run **Evaluate safe policy (5 cases)** to see a deterministic 5/5 with case-level explanations.\n2. Run **Evaluate unsafe policy (5 cases)** to see explicit rejection of fabrication and unverified cache usage.\n3. Run the above Python tests offline to verify consistency and fail-closed scoring.\n4. Inspect `/api/revocation` read-only status; real inference is intentionally disabled after the previous single-use attempt.\n\n**Evidence boundary:** Passing the synthetic policy does not establish that Nemotron chooses correct actions autonomously. The authenticated model catalog returned HTTP 200 and listed Nemotron as available, but a successful end-to-end model recovery response is not yet verified.

## Authenticated NVIDIA Nemotron evidence

Nemotron 3 Nano 30B A3B was queried through Nebius Token Factory in isolated GitHub Actions executions:

- Connectivity: 70 tokens, `READY`, successful API response.
- Recovery assessment: 450 tokens, no visible content after reaching 256-token output budget; functional recovery **not demonstrated**.

The original GitHub Actions logs are associated with a private infrastructure repository, so judges may be unable to view them. We provide a factual summary here but do **not** claim a successful live recovery benchmark.

## Scope and security

This standalone public repository excludes private HG Market System code, credentials, tokens, deployment configuration and trading systems. The five-case public simulation is static: loading the site or pressing simulation controls makes no model API calls. A separately authenticated live inference button exists but its server execution is currently disabled.

Licensed MIT. Copyright © 2026 HG Stack.
