import io, json, socket, unittest, urllib.error
import nebius_manual as nm
from model_cascade import ModelFallbackCascade

GATE = {"NEBIUS_BILLING_GATE": "VERIFIED", "NEBIUS_BILLING_GATE_EVIDENCE": "ref", "NEBIUS_API_KEY": "dummy"}

def no_net(*a, **k):
    raise AssertionError("network call attempted")

class Resp(io.BytesIO):
    headers = {"x-request-id": "req-1"}
    def __enter__(self): return self
    def __exit__(self, *a): pass

class GateTests(unittest.TestCase):
    def test_blocks_without_gate(self):
        for env in ({}, {"NEBIUS_API_KEY": "dummy"}, {"NEBIUS_API_KEY": "d", "NEBIUS_BILLING_GATE": "VERIFIED"}):
            self.assertEqual(nm.run(512, env=env, opener=no_net)["status"], "BLOCKED_BILLING_GATE")
    def test_blocks_without_key(self):
        env = dict(GATE); env.pop("NEBIUS_API_KEY")
        self.assertEqual(nm.run(512, env=env, opener=no_net)["requests"], 0)
    def test_token_ceiling(self):
        with self.assertRaises(SystemExit): nm.run(2048, env=GATE, opener=no_net)
    def test_timeout_and_disconnect_single_attempt(self):
        for exc in (socket.timeout("t"), urllib.error.URLError("down"), ConnectionResetError()):
            calls = []
            def op(req, timeout):
                calls.append(timeout); raise exc
            r = nm.run(512, env=GATE, opener=op)
            self.assertEqual((r["status"], len(calls), calls[0], r["retries"]), ("FAIL", 1, 30, 0))
            self.assertNotIn("dummy", json.dumps(r))
    def test_pass_and_truncated(self):
        body = {"id": "x", "model": nm.MODEL, "usage": {"total_tokens": 9},
                "choices": [{"finish_reason": "stop", "message": {"content": '{"action":"ask_for_source"}'}}]}
        r = nm.run(512, env=GATE, opener=lambda req, timeout: Resp(json.dumps(body).encode()))
        self.assertEqual((r["status"], r["model_returned"], r["provider"]), ("PASS", nm.MODEL, "nebius_token_factory"))
        body["choices"][0]["finish_reason"] = "length"
        r = nm.run(512, env=GATE, opener=lambda req, timeout: Resp(json.dumps(body).encode()))
        self.assertEqual(r["status"], "INCONCLUSIVE")
    def test_fallback_never_labelled_nemotron(self):
        def op(req, timeout=None):
            if "11434" in req.full_url: return Resp(json.dumps({"response": "ok"}).encode())
            raise urllib.error.URLError("down")
        c = ModelFallbackCascade(local_model="qwen3.5:4b", opener=op)
        r = c.execute("p")
        self.assertEqual((r["provider"], r["model"]), ("ollama", "qwen3.5:4b"))
        self.assertNotIn("Nemotron", json.dumps(r) + json.dumps(c.audit_log))

if __name__ == "__main__": unittest.main()
