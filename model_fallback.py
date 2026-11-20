from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ModelInvocationError(Exception):
    """Raised when a specific model invocation fails."""
    pass


class AllModelsFailedError(Exception):
    """Raised when all models in the fallback cascade fail."""
    pass


class ModelClient:
    """Represents an individual model provider or client (e.g., Cloud API or Local Ollama)."""

    def __init__(self, name: str, invoke_func: Callable[[str, Dict[str, Any]], str], is_local: bool = False):
        self.name = name
        self.invoke_func = invoke_func
        self.is_local = is_local

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return self.invoke_func(prompt, kwargs)


class FallbackCascade:
    """Orchestrates deterministic fallback cascade across a prioritized list of model clients."""

    def __init__(self, cascade: Optional[List[ModelClient]] = None):
        self.cascade: List[ModelClient] = cascade or []

    def add_model(self, client: ModelClient) -> None:
        self.cascade.append(client)

    def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes prompt through the cascade sequentially.
        Returns a dict containing 'content', 'model_used', 'is_local', and 'attempts'.
        """
        if not self.cascade:
            raise AllModelsFailedError("No models configured in the fallback cascade.")

        attempts: List[Dict[str, Any]] = []

        for client in self.cascade:
            try:
                logger.info("Attempting generation with model: %s", client.name)
                result = client.generate(prompt, **kwargs)
                attempts.append({"model": client.name, "status": "success"})
                return {
                    "content": result,
                    "model_used": client.name,
                    "is_local": client.is_local,
                    "attempts": attempts,
                }
            except Exception as e:
                logger.warning("Model %s failed: %s. Falling back to next in cascade.", client.name, str(e))
                attempts.append({"model": client.name, "status": "failure", "error": str(e)})

        raise AllModelsFailedError(f"All {len(self.cascade)} models in cascade failed: {attempts}")
