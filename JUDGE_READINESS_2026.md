# Judge Walkthrough & Demonstration Plan (Nebius × NVIDIA Hackathon 2026)

> **Evidence Boundary:** The public 5-case evaluation is deterministic and executes locally in the browser/client, not autonomous Nemotron inference. The live inference endpoint is intentionally disabled by default with a Redis single-use fail-closed gate to protect resources.

---

## Public Entry Points (Verified Free Access)
- **Working Web Demo:** [https://hg-agent-reliability-lab-nebius.vercel.app](https://hg-agent-reliability-lab-nebius.vercel.app) (Verified HTTP 200, requires zero authentication or API keys).
- **Public Source & Scorer:** [https://github.com/hgreco85/HG-Agent-Reliability-Lab](https://github.com/hgreco85/HG-Agent-Reliability-Lab) (MIT License, stdlib Python tests).
- **Demonstration Video:** [https://youtu.be/Fspprw83k0Y](https://youtu.be/Fspprw83k0Y) (Live screen recording showing actual Windows 11 Chrome and terminal execution).
- **Devpost Submission:** [https://nebiusglobalaihackathon.devpost.com/submissions/1233367-hg-agent-reliability-lab](https://nebiusglobalaihackathon.devpost.com/submissions/1233367-hg-agent-reliability-lab).

---

## Real Demonstration Video Script & Shot List (< 3 minutes)

This demonstration shows the real application running interactively on Windows with live browser and terminal execution:

1. **00:00–00:25 | Browser Address & Executive Overview**
   - Visible address bar: `https://hg-agent-reliability-lab-nebius.vercel.app`.
   - Explains the purpose: evaluating AI-agent decision safety when tools fail, timeouts occur, or cache is unverified.
   - Clarifies the evidence boundary: client-side deterministic benchmark vs cloud inference.

2. **00:25–01:10 | Interactive Failure Scenarios & Fail-Closed Logic**
   - Scenario `timeout-unverified-cache`: Click **Run evidence-safe decision** -> Shows `ask_for_source` (`PASS · ok`).
   - Click **Run unsafe decision** -> Demonstrates fail-closed protection against stale data (`FAIL · unverified_source`).
   - Scenario `schema-invalid`: Demonstrates prevention of hallucination / malformed payload ingestion.

3. **01:10–01:45 | Deterministic 5-Case Policy Benchmarks**
   - Click **Evaluate safe policy (5 cases)**: Generates 5/5 PASS matrix with case-by-case rationale.
   - Click **Evaluate unsafe policy (5 cases)**: Generates 0/5 FAIL matrix rejecting all unverified cache fallbacks and hallucinations.

4. **01:45–02:20 | Local Offline Reproducibility (Windows Terminal)**
   - Terminal demonstration: `python evaluator.py` running in Windows cmd/PowerShell.
   - Execution of unit test suite: `python -m unittest discover -v` (35 tests pass in < 0.05s).
   - Shows total independence from external network dependencies or paid APIs.

5. **02:20–02:45 | NVIDIA Nemotron & Nebius Token Factory Evidence**
   - Inspection of documented CI logs: Run 38189289839 (70 tokens, PASS: READY) and Run 38190116887 (450 tokens, INCONCLUSIVE recovery).
   - Architecture review of the persistent one-shot Redis gate (`claim_once`) guaranteeing $0 unintended spend.

6. **02:45–02:55 | Conclusion & Free Evaluator Access**
   - Reiteration of unauthenticated, zero-cost access for Devpost evaluators.

---

## Verifiable Acceptance Checklist
- [x] Web demo opens in Chrome/Edge without authentication or credentials (HTTP 200).
- [x] All 5 failure scenarios execute interactively with safe and unsafe policy paths.
- [x] Safe suite passes 5/5; unsafe suite detects 100% of policy violations (0/5).
- [x] Python evaluator and all 35 unit tests run cleanly offline in Windows.
- [x] Open-source MIT license present and detected in repository.
- [x] Strict cost controls and single-use Redis gate verified.
- [x] Real screen recording of Windows browser and terminal execution generated.
- [ ] Final video URL placed in the dedicated Devpost video field (awaiting user approval before submission).

---

## Devpost Submission Text & Instructions for Judges

### Pitch / Short Summary
Evidence-first AI agent reliability lab auditing tool-failure recovery, hallucination rejection, and NVIDIA Nemotron 3 Nano 30B integration on Nebius Token Factory.

### Instructions for Testing
Open https://hg-agent-reliability-lab-nebius.vercel.app in any web browser (no login or API key required). Test any scenario with safe and unsafe actions, then run the 5-case policy benchmarks. To inspect offline, clone https://github.com/hgreco85/HG-Agent-Reliability-Lab and run `python evaluator.py` and `python -m unittest discover -v`.
