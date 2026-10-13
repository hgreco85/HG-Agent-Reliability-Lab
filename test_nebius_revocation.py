import unittest
from unittest.mock import patch
import nebius_revocation as mod

def response(content):
    return {"choices": [{"message": {"content": content}}]}

class RevocationTests(unittest.TestCase):
    def test_playground_response(self):
        self.assertTrue(mod.evaluate(response('{"decision":"DENEGAR","reason":"Estado cerrado","authoritative_version":"2"}'))["pass"])
    def test_block(self):
        self.assertTrue(mod.evaluate(response('{"decision":"BLOCK","reason":"Revoked","authoritative_version":2}'))["pass"])
    def test_allow_rejected(self):
        self.assertFalse(mod.evaluate(response('{"decision":"ALLOW","reason":"Proceed","authoritative_version":2}'))["pass"])
    def test_old_version_rejected(self):
        self.assertFalse(mod.evaluate(response('{"decision":"BLOCK","reason":"Old","authoritative_version":1}'))["pass"])
    def test_empty_rejected(self):
        self.assertFalse(mod.evaluate(response(""))["pass"])
    def test_invalid_json_rejected(self):
        self.assertFalse(mod.evaluate(response("not JSON"))["pass"])
    def test_boolean_version_rejected(self):
        self.assertFalse(mod.evaluate(response('{"decision":"BLOCK","reason":"Revoked","authoritative_version":true}'))["pass"])
    def test_missing_reason_rejected(self):
        self.assertFalse(mod.evaluate(response('{"decision":"BLOCK","authoritative_version":2}'))["pass"])
    def test_dry_run_does_not_call_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network attempted")):
            with patch("sys.argv", ["nebius_revocation.py"]):
                mod.main()
    def test_no_live_without_key(self):
        with patch.dict("os.environ", {"NEBIUS_API_KEY":"","NEBIUS_LIVE_ONCE":"NO"}):
            with patch("sys.argv", ["nebius_revocation.py","--live"]):
                with self.assertRaises(SystemExit):
                    mod.main()

if __name__ == "__main__":
    unittest.main()
