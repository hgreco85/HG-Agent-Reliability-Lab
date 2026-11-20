from __future__ import annotations

import unittest
from typing import Any, Dict
from unittest.mock import MagicMock

from model_fallback import AllModelsFailedError, FallbackCascade, ModelClient, ModelInvocationError


class TestModelFallbackCascade(unittest.TestCase):

    def setUp(self) -> None:
        self.cloud_mock = MagicMock()
        self.cloud_secondary_mock = MagicMock()
        self.ollama_mock = MagicMock()

        self.cloud_client = ModelClient(
            name="cloud-primary",
            invoke_func=self.cloud_mock,
            is_local=False,
        )
        self.cloud_secondary_client = ModelClient(
            name="cloud-secondary",
            invoke_func=self.cloud_secondary_mock,
            is_local=False,
        )
        self.ollama_client = ModelClient(
            name="local-ollama",
            invoke_func=self.ollama_mock,
            is_local=True,
        )

        self.cascade = FallbackCascade([
            self.cloud_client,
            self.cloud_secondary_client,
            self.ollama_client,
        ])

    def test_primary_cloud_success_no_fallback(self) -> None:
        """When primary cloud model succeeds, local Ollama should not be called."""
        self.cloud_mock.return_value = "Response from primary cloud"

        res = self.cascade.execute("Test prompt")

        self.assertEqual(res["content"], "Response from primary cloud")
        self.assertEqual(res["model_used"], "cloud-primary")
        self.assertFalse(res["is_local"])
        self.assertEqual(len(res["attempts"]), 1)
        self.assertEqual(res["attempts"][0]["status"], "success")

        self.cloud_mock.assert_called_once_with("Test prompt", {})
        self.cloud_secondary_mock.assert_not_called()
        self.ollama_mock.assert_not_called()

    def test_graceful_degradation_to_local_ollama(self) -> None:
        """When all cloud models fail, deterministically degrade to local Ollama."""
        self.cloud_mock.side_effect = ModelInvocationError("503 Service Unavailable: Cloud API Rate Limit")
        self.cloud_secondary_mock.side_effect = ModelInvocationError("500 Internal Server Error: Gateway Timeout")
        self.ollama_mock.return_value = "Response from local Ollama (llama3)"

        res = self.cascade.execute("Summarize this context")

        self.assertEqual(res["content"], "Response from local Ollama (llama3)")
        self.assertEqual(res["model_used"], "local-ollama")
        self.assertTrue(res["is_local"])

        self.assertEqual(len(res["attempts"]), 3)
        self.assertEqual(res["attempts"][0]["status"], "failure")
        self.assertEqual(res["attempts"][0]["model"], "cloud-primary")
        self.assertEqual(res["attempts"][1]["status"], "failure")
        self.assertEqual(res["attempts"][1]["model"], "cloud-secondary")
        self.assertEqual(res["attempts"][2]["status"], "success")
        self.assertEqual(res["attempts"][2]["model"], "local-ollama")

        self.cloud_mock.assert_called_once()
        self.cloud_secondary_mock.assert_called_once()
        self.ollama_mock.assert_called_once()

    def test_all_models_including_ollama_fail_raises_exception(self) -> None:
        """When cloud models and local Ollama all fail, AllModelsFailedError is raised with telemetry."""
        self.cloud_mock.side_effect = ConnectionError("Network unreachable")
        self.cloud_secondary_mock.side_effect = TimeoutError("Connection timed out")
        self.ollama_mock.side_effect = ModelInvocationError("Ollama daemon not running")

        with self.assertRaises(AllModelsFailedError) as ctx:
            self.cascade.execute("Critical calculation prompt")

        err_msg = str(ctx.exception)
        self.assertIn("All 3 models in cascade failed", err_msg)
        self.assertIn("Network unreachable", err_msg)
        self.assertIn("Ollama daemon not running", err_msg)

        self.cloud_mock.assert_called_once()
        self.cloud_secondary_mock.assert_called_once()
        self.ollama_mock.assert_called_once()

    def test_empty_cascade_raises_error(self) -> None:
        """Verify behavior when no models are present in cascade."""
        empty_cascade = FallbackCascade()
        with self.assertRaises(AllModelsFailedError):
            empty_cascade.execute("Hello world")


if __name__ == "__main__":
    unittest.main()
