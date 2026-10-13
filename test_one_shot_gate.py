import json
import os
import unittest
from unittest.mock import patch
from api import revocation as api

ENV = {"NEBIUS_API_KEY": "dummy", "HG_DEMO_ACCESS_TOKEN": "test-token",
       "KV_REST_API_URL": "https://example.upstash.io",
       "KV_REST_API_TOKEN": "dummy", "KV_REST_API_READ_ONLY_TOKEN": "read-only", "HG_NEBIUS_LIVE_ENABLED": "YES"}

class FakeResponse:
    def __init__(self, result): self.result = result
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return json.dumps(self.result).encode()

class OneShotTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {**ENV, "HG_NEBIUS_LIVE_ENABLED": ""}, clear=True):
            self.assertFalse(api.ready())
    def test_masked_nebius_secret_disables_live(self):
        for bad_key in ("masked***", " spaces ", "key\n"):
            with self.subTest(key_type=repr(bad_key)):
                with patch.dict(os.environ, {**ENV, "NEBIUS_API_KEY": bad_key}, clear=True):
                    self.assertFalse(api.ready())

    def test_missing_store_disables(self):
        with patch.dict(os.environ, {**ENV, "KV_REST_API_TOKEN": ""}, clear=True):
            self.assertFalse(api.ready())
    def test_atomic_set_nx(self):
        def check(req, timeout):
            self.assertEqual(json.loads(req.data), ["SET", api.GATE_KEY, "spent", "NX"])
            return FakeResponse({"result": "OK"})
        with patch.dict(os.environ, ENV, clear=True), patch("urllib.request.urlopen", side_effect=check):
            self.assertTrue(api.claim_once())
    def test_repeated_call_rejected(self):
        with patch.dict(os.environ, ENV, clear=True), patch("urllib.request.urlopen", return_value=FakeResponse({"result": None})):
            self.assertFalse(api.claim_once())
    def test_store_error_rejected(self):
        with patch.dict(os.environ, ENV, clear=True), patch("urllib.request.urlopen", side_effect=TimeoutError):
            self.assertFalse(api.claim_once())
    def test_read_only_gate_spent(self):
        def check(req, timeout):
            self.assertEqual(json.loads(req.data), ["GET", api.GATE_KEY])
            self.assertEqual(req.headers["Authorization"], "Bearer read-only")
            return FakeResponse({"result": "spent"})
        with patch.dict(os.environ, ENV, clear=True), patch("urllib.request.urlopen", side_effect=check):
            self.assertEqual(api.gate_status(), "SPENT")
    def test_read_only_gate_unused(self):
        with patch.dict(os.environ, ENV, clear=True), patch("urllib.request.urlopen", return_value=FakeResponse({"result": None})):
            self.assertEqual(api.gate_status(), "UNUSED")
    def test_read_only_gate_unknown_on_error(self):
        with patch.dict(os.environ, ENV, clear=True), patch("urllib.request.urlopen", side_effect=TimeoutError):
            self.assertEqual(api.gate_status(), "UNKNOWN")
    def test_insecure_url_rejected(self):
        with patch.dict(os.environ, {**ENV, "KV_REST_API_URL": "http://localhost"}, clear=True):
            self.assertFalse(api.claim_once())


    def test_upstream_status_preserved_without_retry(self):
        import urllib.error
        from unittest.mock import MagicMock
        for code in (401, 403, 429, 500):
            with self.subTest(upstream_status=code):
                instance = object.__new__(api.handler)
                instance.headers = {"X-Demo-Token": "test-token", "Content-Length": "0"}
                instance.reply = MagicMock()
                err = urllib.error.HTTPError("https://example.invalid", code, "mock", {}, None)
                with patch.dict(os.environ, ENV, clear=True), \
                     patch.object(api, "claim_once", return_value=True) as claim, \
                     patch("urllib.request.urlopen", side_effect=err) as upstream:
                    instance.do_POST()
                claim.assert_called_once()
                upstream.assert_called_once()
                args = instance.reply.call_args.args
                self.assertEqual(args[0], 502)
                self.assertEqual(args[1]["upstream_status"], code)
                self.assertFalse(args[1]["live_api"])

    def test_spent_gate_never_calls_model(self):
        from unittest.mock import MagicMock
        instance = object.__new__(api.handler)
        instance.headers = {"X-Demo-Token": "test-token", "Content-Length": "0"}
        instance.reply = MagicMock()
        with patch.dict(os.environ, ENV, clear=True), \
             patch.object(api, "claim_once", return_value=False), \
             patch("urllib.request.urlopen", side_effect=AssertionError("model call forbidden")):
            instance.do_POST()
        self.assertEqual(instance.reply.call_args.args[0], 409)

if __name__ == "__main__":
    unittest.main()
