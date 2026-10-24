import io
import json
import unittest
import urllib.error
import urllib.request
from model_cascade import ModelCascadeError, ModelFallbackCascade


class FakeHTTPResponse:
    def __init__(self, status_code: int, data: dict):
        self.status = status_code
        self.code = status_code
        self._data = json.dumps(data).encode("utf-8")
        self._stream = io.BytesIO(self._data)

    def read(self, *args, **kwargs):
        return self._stream.read(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestModelFallbackCascade(unittest.TestCase):
    def test_primary_cloud_success_no_fallback(self):
        cloud_payload = {
            "model": "cloud-frontier-model",
            "choices": [{"message": {"content": "Cloud response here."}}],
        }

        def mock_opener(request, timeout=None):
            if "api.cloud-provider.internal" in request.full_url:
                return FakeHTTPResponse(200, cloud_payload)
            raise AssertionError("Local Ollama should not be reached when cloud succeeds")

        cascade = ModelFallbackCascade(opener=mock_opener)
        result = cascade.execute("Hello AI")

        self.assertEqual(result["source"], "cloud")
        self.assertEqual(result["content"], "Cloud response here.")
        self.assertEqual(len(cascade.audit_log), 1)
        self.assertEqual(cascade.audit_log[0]["stage"], "cloud")
        self.assertEqual(cascade.audit_log[0]["status"], "success")

    def test_cloud_fails_with_500_falls_back_to_local_ollama(self):
        local_payload = {"response": "Ollama local inference response."}

        def mock_opener(request, timeout=None):
            if "api.cloud-provider.internal" in request.full_url:
                fp = io.BytesIO(b"500 Internal Server Error")
                raise urllib.error.HTTPError(
                    url=request.full_url,
                    code=500,
                    msg="Internal Server Error",
                    hdrs={},
                    fp=fp,
                )
            elif "11434" in request.full_url:
                return FakeHTTPResponse(200, local_payload)
            raise ValueError(f"Unexpected request url: {request.full_url}")

        cascade = ModelFallbackCascade(opener=mock_opener)
        result = cascade.execute("Test prompt under cloud degradation")

        self.assertEqual(result["source"], "local_ollama")
        self.assertEqual(result["content"], "Ollama local inference response.")
        self.assertEqual(len(cascade.audit_log), 2)
        self.assertEqual(cascade.audit_log[0]["stage"], "cloud")
        self.assertEqual(cascade.audit_log[0]["status"], "failure")
        self.assertEqual(cascade.audit_log[0]["error_type"], "HTTPError")
        self.assertEqual(cascade.audit_log[1]["stage"], "local_ollama")
        self.assertEqual(cascade.audit_log[1]["status"], "success")

    def test_cloud_timeout_falls_back_to_local_ollama(self):
        local_payload = {"response": "Fallback after cloud timeout."}

        def mock_opener(request, timeout=None):
            if "api.cloud-provider.internal" in request.full_url:
                raise TimeoutError("Connection to cloud provider timed out")
            elif "11434" in request.full_url:
                return FakeHTTPResponse(200, local_payload)
            raise ValueError(f"Unexpected request url: {request.full_url}")

        cascade = ModelFallbackCascade(opener=mock_opener)
        result = cascade.execute("Prompt when network to cloud hangs")

        self.assertEqual(result["source"], "local_ollama")
        self.assertEqual(result["content"], "Fallback after cloud timeout.")
        self.assertEqual(cascade.audit_log[0]["stage"], "cloud")
        self.assertEqual(cascade.audit_log[0]["error_type"], "TimeoutError")
        self.assertEqual(cascade.audit_log[1]["stage"], "local_ollama")
        self.assertEqual(cascade.audit_log[1]["status"], "success")

    def test_both_cloud_and_local_fail_raises_cascade_error(self):
        def mock_opener(request, timeout=None):
            if "api.cloud-provider.internal" in request.full_url:
                fp = io.BytesIO(b"503 Service Unavailable")
                raise urllib.error.HTTPError(
                    url=request.full_url,
                    code=503,
                    msg="Service Unavailable",
                    hdrs={},
                    fp=fp,
                )
            elif "11434" in request.full_url:
                raise urllib.error.URLError("Connection refused - Ollama daemon offline")
            raise ValueError(f"Unexpected URL: {request.full_url}")

        cascade = ModelFallbackCascade(opener=mock_opener)
        with self.assertRaises(ModelCascadeError) as ctx:
            cascade.execute("Prompt when both fail")

        self.assertIn("All providers failed", str(ctx.exception))
        self.assertEqual(len(cascade.audit_log), 2)
        self.assertEqual(cascade.audit_log[0]["status"], "failure")
        self.assertEqual(cascade.audit_log[1]["status"], "failure")


if __name__ == "__main__":
    unittest.main()
