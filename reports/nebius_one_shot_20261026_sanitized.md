# Nebius × NVIDIA — sanitized one-shot evidence (2026-10-26)

Evidence status: **reported successful real inference**; receipt transcribed from the existing PR #7 execution comment. This report is not a new model call or an independent billing statement.

- Canonical task: `nebius-zero-charge-e2e-20261026`
- Source: https://github.com/hgreco85/HG-Agent-Reliability-Lab/pull/7#issuecomment-6428145657
- Workflow run: https://github.com/hgreco85/HG-Market-System/actions/runs/40407357142
- Workflow execution commit: `c939eba`; self-hosted Windows runner `hg-local`
- Time: 2026-10-26 21:48:13 UTC / 18:48:13 ART
- Provider: Nebius Token Factory, `api.tokenfactory.nebius.com/v1/chat/completions`
- Model requested/reported: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`
- Request ID: `chatcmpl-63ee3ada-ee46-4951-87f7-335066ea3e1e`
- Requests: 1; retries: 0; timeout: 30 s; maximum output tokens: 1024
- Reported latency: 1.966 seconds; finish_reason: `stop`
- Usage: 86 prompt + 230 completion = 316 total tokens
- Synthetic scenario: unavailable document source, unverified cache, no retries
- Expected action: `ask_for_source`; reported response: `{"action":"ask_for_source","reason":"need verified source to avoid using unverified cache"}`
- Assessment: **PASS for this single synthetic abstention case only**. Not evidence of a general model benchmark or live Ollama fallback.
- Actual billed amount / credits debited: **NOT VERIFIED**; previous public-tariff calculation is an estimate, not a final charge.

## Reproduction without inference

```sh
python -m unittest discover -v
python -m unittest discover -s tests -v
python evaluator.py
python nebius_manual.py
```

The last command is explicitly dry-run and must return `BLOCKED_DRY_RUN` with zero requests. Do **not** pass `--live`; do not set billing-gate or API-key environment variables for this audit. Earlier PR commentary reports 35/35 root and 10/10 tests-directory passes at commit `9b787cc`; these numbers are **historical** pending fresh clean-clone execution.

## Submission gate

Official rules: https://nebiusglobalaihackathon.devpost.com/rules
Deadline: 2026-10-30 14:00 ART. Public repo and MIT license verified in GitHub metadata. Public demo and YouTube URLs are linked from README but must be opened and validated as functioning/accessible, and video duration checked. Devpost submission 1233367 editability/state is **UNVERIFIED** without authenticated access. Do not submit or edit without owner approval. Confirm final credit usage from read-only Nebius billing console; do not infer net USD 0 from credit balance.
