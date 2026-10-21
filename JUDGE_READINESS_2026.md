# Judge walkthrough and real-demo recording plan (Nebius × NVIDIA, October 2026)

> **Evidence boundary:** The public 5-case evaluation is deterministic and executes locally in the browser, not autonomous Nemotron inference. The live inference endpoint is currently disabled. Do not present any synthetic output as a live model response.

## Public entry points
- Working demo candidate: https://hg-agent-reliability-lab-nebius.vercel.app
- Source and reproducible evaluator: https://github.com/hgreco85/HG-Agent-Reliability-Lab
- Existing YouTube video: https://youtu.be/44dX_pD3OMo
- Devpost submission: https://nebiusglobalaihackathon.devpost.com/submissions/1233367-hg-agent-reliability-lab

**Not yet independently verified:** public HTTP availability, video playback and suitability, and whether the YouTube URL was placed in the *Devpost video field*. All must be checked in an incognito window before declaring compliance.

## Three-minute screen recording shot list (record actual footage, not mock-ups)
1. **00:00–00:20 | Browser address visible:** Launch the deployed app in an incognito browser. State what it evaluates; explain clearly that this part is a deterministic reliability policy test.
2. **00:20–01:00 | Interactive user actions:** Select a failure scenario; press **Run evidence-safe decision**, read explanation, switch to **Run unsafe decision**, show fail-closed verdict.
3. **01:00–01:45 | Full suite:** Click **Evaluate safe policy (5 cases)**. Show case-level outcomes, then **Evaluate unsafe policy (5 cases)**. Do not overlay invented model outputs.
4. **01:45–02:20 | Source reproducibility:** Show the public repository and evaluator.py. In a local terminal execute `python evaluator.py` and `python -m unittest test_evaluator.py test_demo_contract.py -v`; only state PASS if these commands genuinely pass on camera.
5. **02:20–02:45 | NVIDIA/Nebius connection boundary:** Show the 'Real Nebius evidence' section, distinguishing successful connectivity from inconclusive recovery. Point out authenticated live inference is disabled; do not attempt a metered request.
6. **02:45–03:00 | Judge access:** Return to the public browser tab; emphasize free accessible interactive demo and public code.

## Spoken narration (English)
“HG Agent Reliability Lab examines what an agent should do when its tools time out, evidence is missing, or cached information is not verified. This interactive public version uses deterministic test scenarios, so its scores are reproducible and should not be mistaken for live language-model accuracy. Here I choose a failure and run the evidence-safe decision. The tool is unable to provide verified evidence, so the policy does not invent an answer. I can also try an unsafe decision, and the evaluator flags it. Next I run the five-case suite, compare safe and unsafe policies, and see each decision explained. The same tests can run locally using the Python evaluator and unit tests in this public repository. The project separately investigated NVIDIA Nemotron through Nebius Token Factory: connectivity succeeded, but a later recovery trial was inconclusive, and live inference is currently disabled to protect resources. Judges can access the public interactive demonstration and inspect or run the open-source evaluator without credentials or charges.”

## Acceptance checklist
- [ ] Published video actually plays, showing real device/browser footage of project functionality.
- [ ] Video URL is in the dedicated Devpost video field; not merely in GitHub README or description.
- [ ] Site opens in a private browser without sign-in or payment; the safe and unsafe buttons and five-case evaluations actually respond.
- [ ] Public source is available, tests run locally, and on-screen claims match logs.
- [ ] No externally exposed unrestricted live inference or secrets.
- [ ] Devpost testing instructions include public demo URL, clear click path, GitHub source, Python test command, and disclosure of disabled inference.
- [ ] Any mandated genuine NVIDIA-model usage is evaluated accurately against contest rules; no unsupported claims.
- [ ] Submission updated and organizer notified **only after user approval**.

## Devpost judge testing instructions (paste draft)
Open https://hg-agent-reliability-lab-nebius.vercel.app in a desktop browser. Under the interactive reliability benchmark, choose a tool-failure scenario and click “Run evidence-safe decision”; then “Run unsafe decision” to compare explanations and verdicts. Run both five-case evaluations. This public deterministic demonstration requires no login, API key, or payment. Source and local Python evaluator: https://github.com/hgreco85/HG-Agent-Reliability-Lab. To reproduce, execute `python evaluator.py` and `python -m unittest test_evaluator.py test_demo_contract.py -v`. Synthetic policy scoring is not live Nemotron inference; the README describes authenticated Nebius connectivity evidence and the inconclusive recovery trial. Server-side live inference remains disabled.

## Organizer response (DRAFT — do not send without approval)
Thank you for flagging the video and judging-access requirements. We have a public interactive project demo at https://hg-agent-reliability-lab-nebius.vercel.app and public code at https://github.com/hgreco85/HG-Agent-Reliability-Lab. We are verifying the demonstration footage and its placement in the required Devpost video field, and will correct the submission before October 30 at 10 a.m. PT. We will also ensure the judge instructions accurately distinguish the deterministic interactive evaluation from the limited authenticated NVIDIA/Nebius evidence. Thank you for the opportunity to complete the submission.

## Execution provenance
Prepared as an actionable remediation plan, not evidence that a video was published, a website checked, or the Devpost form edited.
