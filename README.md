# HG Agent Reliability Lab

Evidence-first AI-agent reliability prototype, built for the **Nebius × NVIDIA Global AI Hackathon 2026**.

**[Interactive demo](https://hg-agent-reliability-lab-nebius.vercel.app)** · **[Video demonstration](https://youtu.be/44dX_pD3OMo)**

## What it does

A small, independent browser demo and Python scorer show how to audit an agent's behavior when tools fail, a document cannot be retrieved, or cached information is unverified. The browser demo uses **simulated decisions**; it is not an agent inference endpoint.

## Usage

Open `index.html` directly in a browser. Offline scoring requires Python 3:

```sh
python evaluator.py
python -m unittest test_evaluator.py -v
```

No third-party packages or API key are required to run the public demo and scorer.

## Authenticated NVIDIA Nemotron evidence

Nemotron 3 Nano 30B A3B was queried through Nebius Token Factory in isolated GitHub Actions executions:

- Connectivity: 70 tokens, `READY`, successful API response.
- Recovery assessment: 450 tokens, no visible content after reaching 256-token output budget; functional recovery **not demonstrated**.

The original GitHub Actions logs are associated with a private infrastructure repository, so judges may be unable to view them. We provide a factual summary here but do **not** claim a successful live recovery benchmark.

## Scope and security

This standalone public repository excludes private HG Market System code, credentials, tokens, deployment configuration and trading systems. The current public demo is static. No API calls are made by opening this site.

Licensed MIT. Copyright © 2026 HG Stack.
