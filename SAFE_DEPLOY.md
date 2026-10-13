# HG Agent Reliability Lab — secure one-shot rollout

The Vercel endpoint is **disabled by default**. CI uses mocks and never calls Nebius.

## Server-only secrets and flags
- `NEBIUS_API_KEY`: Sensitive, already present in Vercel; validity is unverified.
- `HG_DEMO_ACCESS_TOKEN`: independent random secret, Sensitive; never put Nebius API key in webpage.
- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`: Sensitive; use one dedicated free Redis REST database with verified non-billable hard limits.
- `HG_NEBIUS_LIVE_ENABLED`: must equal `YES` to allow live requests. Keep absent until everything is checked.

## One-shot invariant

The only live route claims `SET hg-agent-reliability-lab:nebius:revocation:v1:spent spent NX` via an atomic Redis REST request. The key **never expires** and is **never deleted**, even if Nebius times out or rejects authentication. All production instances must share this same Redis. Don't swap storage, modify the key, or enable preview simultaneously. Any Redis error fails closed. A second request returns HTTP 409 without calling Nebius.

## Before enablement

1. Confirm a genuine hard monetary/token cap or exclusively free no-overage quota **on the Nebius provider account**. Do not infer this from `max_tokens`.
2. Verify the free Redis database cannot incur surprise charges; if that guarantee cannot be established, leave disabled.
3. Verify Vercel Git linking and that CI passes; merge only after review and make a safe redeploy.
4. Verify GET `/api/revocation` reports `DISABLED`, with no model call.
5. Only then configure all secrets privately and enable the flag for **production only**. One authenticated POST with no request body claims the permit. Save status, decision, and usage; **never retry**.
6. GET `READY` means environment/configuration exists, **not** that Nebius authentication was validated.

If any prerequisite fails, the correct action is to keep live access disabled. No local or CI test demonstrates that a paid live request has succeeded.
