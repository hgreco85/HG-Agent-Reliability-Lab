# HG Agent Reliability Lab

Evidence-first AI-agent reliability prototype, built for the **Nebius × NVIDIA Global AI Hackathon 2026**.

**[Interactive Demo](https://hg-agent-reliability-lab-nebius.vercel.app)** · **[Video Demonstration](https://youtu.be/Fspprw83k0Y)** · **[Code Repository](https://github.com/hgreco85/HG-Agent-Reliability-Lab)**

---

## What it does

**HG Agent Reliability Lab** evaluates how autonomous AI agents respond when tools fail, network calls time out, or data caches contain unverified summaries. 

The project delivers:
1. **Interactive Browser Benchmark:** A client-side evaluator demonstrating 5 distinct tool-failure topologies, comparing *evidence-safe* decisions against *unsafe* fallbacks (preventing hallucination/fabrication and stale cache leakage).
2. **Deterministic Offline Evaluator:** A Python stdlib scorer and test suite validating fail-closed behavior with zero external dependencies.
3. **Hardware & Model Integration Boundary:** Complete documentation and test harnesses auditing NVIDIA Nemotron 3 Nano 30B A3B hosted via Nebius Token Factory, with a persistent one-shot Redis safety gate to guarantee zero unauthorized cloud spend.

> **Evidence boundary:** The 5-case interactive demo and Python evaluator run deterministic synthetic policies locally without model inference. This isolates and audits the decision policy independently of model stochasticity.

---

## Instructions for Hackathon Judges

Judges can verify the entire project without accounts, API keys, or fees:

### 1. Web Evaluation (No credentials required)
1. Open the public web demo: **[https://hg-agent-reliability-lab-nebius.vercel.app](https://hg-agent-reliability-lab-nebius.vercel.app)**.
2. Select any tool failure scenario (e.g., `timeout-unverified-cache`) and click **Run evidence-safe decision** to see the compliant policy action (`ask_for_source`, `PASS · ok`).
3. Click **Run unsafe decision** to see the fail-closed rejection (`FAIL · unverified_source`).
4. Click **Evaluate safe policy (5 cases)** to verify 5/5 compliance across all topologies.
5. Click **Evaluate unsafe policy (5 cases)** to confirm immediate rejection (0/5) of unverified cache and fabrication attempts.
6. Inspect the live inference section: verify it rejects unauthenticated runs and reports status `DISABLED` safely.

### 2. Local Offline Reproduction (Python 3 stdlib only)
Clone the repository and run the test suite:
```sh
git clone https://github.com/hgreco85/HG-Agent-Reliability-Lab.git
cd HG-Agent-Reliability-Lab
python evaluator.py
python -m unittest discover -v
```
All 35 unit tests and contract checks execute in less than 0.1 seconds with zero external package installations.

---

## Authenticated NVIDIA Nemotron Evidence

NVIDIA Nemotron 3 Nano 30B A3B was evaluated via Nebius Token Factory in isolated CI executions:

| Evaluation Stage | Tokens | Status | Findings |
|---|---|---|---|
| **Connectivity & Model Catalog** | 70 tokens | **PASS: READY** | Authenticated endpoint reachable; model listed and responding. |
| **Recovery Assessment** | 450 tokens | **INCONCLUSIVE** | HTTP 200 returned; empty visible content after exhausting the 256 output token budget. Functional autonomous recovery not demonstrated. |

To adhere to the hackathon's strict factual standards, we report exact findings and do **not** misrepresent synthetic benchmark passes as live model recoveries.

---

## Architecture and Safety Gate

- **Client Layer:** Static HTML5/Vanilla JS. Zero client-side API keys, zero tracking, works 100% offline.
- **Serverless Endpoint:** `/api/revocation` implemented with an atomic Redis `SET NX` single-use gate (`claim_once`).
- **Cost Invariant:** Zero incremental cost guarantee ($0). The live model endpoint is disabled by default to prevent credit exhaustion.

---

## Scope & Licensing

This public repository contains the standalone benchmark, test contracts, and verification harnesses. It is decoupled from private upstream trading or execution systems.

Licensed under the **MIT License**. Copyright © 2026 HG Stack.
