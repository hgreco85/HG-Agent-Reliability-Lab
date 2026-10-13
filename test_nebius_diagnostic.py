import json
import os
import unittest
from unittest.mock import patch
from api import nebius_diagnostic as probe

BASE = {"VERCEL_ENV":"production","HG_CATALOG_CHECK_ENABLED":"YES",
        "NEBIUS_API_KEY":"dummy-key", "KV_REST_API_URL":"https://redis.example",
        "KV_REST_API_TOKEN":"dummy"}

class Reply:
    def __init__(self, payload, status=200):
        self.payload=payload
        self.status=status
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return json.dumps(self.payload).encode()

class DiagnosticTests(unittest.TestCase):
    def test_disabled_no_requests(self):
        with patch.dict(os.environ,{**BASE,"HG_CATALOG_CHECK_ENABLED":"NO"},clear=True),patch("urllib.request.urlopen",side_effect=AssertionError("network")):
            self.assertEqual(probe.inspect_once()[0]["status"],"DISABLED")
    def test_masked_key_no_model_requests(self):
        with patch.dict(os.environ,{**BASE,"NEBIUS_API_KEY":"abc***"},clear=True),patch.object(probe,"reserve",return_value=True),patch("urllib.request.urlopen",side_effect=AssertionError("network")):
            self.assertEqual(probe.inspect_once()[0]["status"],"INVALID_KEY_FORMAT")
    def test_reservation_failure_no_requests(self):
        with patch.dict(os.environ,BASE,clear=True),patch.object(probe,"reserve",return_value=False),patch("urllib.request.urlopen",side_effect=AssertionError("network")):
            self.assertEqual(probe.inspect_once()[0]["status"],"ALREADY_CHECKED_OR_GATE_UNAVAILABLE")
    def test_catalog_authorized(self):
        def do_request(req,timeout=None):
            self.assertEqual(req.full_url,probe.CATALOG)
            self.assertEqual(req.get_header("Authorization"),"Bearer dummy-key")
            return Reply({"data":[{"id":probe.EXPECTED}]})
        with patch.dict(os.environ,BASE,clear=True),patch.object(probe,"reserve",return_value=True),patch("urllib.request.urlopen",side_effect=do_request) as fn:
            outcome,status=probe.inspect_once()
            self.assertEqual(status,200)
            self.assertTrue(outcome["model_available"])
            fn.assert_called_once()
    def test_error_preserved(self):
        import urllib.error
        with patch.dict(os.environ,BASE,clear=True),patch.object(probe,"reserve",return_value=True),patch("urllib.request.urlopen",side_effect=urllib.error.HTTPError(probe.CATALOG,401,"Unauthorized",{},None)):
            outcome,status=probe.inspect_once()
            self.assertEqual(status,502)
            self.assertEqual(outcome["upstream_http"],401)

if __name__=="__main__":
    unittest.main()
