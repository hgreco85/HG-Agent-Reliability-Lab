import json
from typing import Any, Callable, Dict, List, Optional
import urllib.error
import urllib.request


class ModelCascadeError(Exception):
    """Raised when all model providers in the cascade fail."""
    pass


def call_cloud_api(
    prompt: str,
    api_url: str = "https://api.cloud-provider.internal/v1/chat/completions",
    api_key: Optional[str] = None,
    opener: Optional[Callable[[urllib.request.Request], Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    payload = json.dumps({
        "model": "cloud-frontier-model",
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
    open_fn = opener or urllib.request.urlopen

    with open_fn(req, timeout=timeout) as resp:
        data = resp.read()
        parsed = json.loads(data.decode("utf-8"))
        content = parsed["choices"][0]["message"]["content"]
        return {"source": "cloud", "content": content, "model": parsed.get("model", "cloud-frontier-model")}


def call_local_ollama(
    prompt: str,
    api_url: str = "http://127.0.0.1:11434/api/generate",
    model_name: str = "llama3",
    opener: Optional[Callable[[urllib.request.Request], Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    payload = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    open_fn = opener or urllib.request.urlopen

    with open_fn(req, timeout=timeout) as resp:
        data = resp.read()
        parsed = json.loads(data.decode("utf-8"))
        return {"source": "local_ollama", "content": parsed["response"], "model": model_name}


class ModelFallbackCascade:
    """Cascades queries from primary cloud provider to a local Ollama instance on failure."""

    def __init__(
        self,
        cloud_url: str = "https://api.cloud-provider.internal/v1/chat/completions",
        local_url: str = "http://127.0.0.1:11434/api/generate",
        local_model: str = "llama3",
        cloud_api_key: Optional[str] = None,
        timeout: float = 5.0,
        opener: Optional[Callable[[urllib.request.Request], Any]] = None,
    ):
        self.cloud_url = cloud_url
        self.local_url = local_url
        self.local_model = local_model
        self.cloud_api_key = cloud_api_key
        self.timeout = timeout
        self.opener = opener
        self.audit_log: List[Dict[str, Any]] = []

    def execute(self, prompt: str) -> Dict[str, Any]:
        # 1. Attempt Cloud
        try:
            result = call_cloud_api(
                prompt=prompt,
                api_url=self.cloud_url,
                api_key=self.cloud_api_key,
                opener=self.opener,
                timeout=self.timeout,
            )
            self.audit_log.append({"stage": "cloud", "status": "success"})
            return result
        except Exception as cloud_err:
            self.audit_log.append({
                "stage": "cloud",
                "status": "failure",
                "error": str(cloud_err),
                "error_type": cloud_err.__class__.__name__,
            })

        # 2. Fallback to Local Ollama
        try:
            result = call_local_ollama(
                prompt=prompt,
                api_url=self.local_url,
                model_name=self.local_model,
                opener=self.opener,
                timeout=self.timeout,
            )
            self.audit_log.append({"stage": "local_ollama", "status": "success"})
            return result
        except Exception as local_err:
            self.audit_log.append({
                "stage": "local_ollama",
                "status": "failure",
                "error": str(local_err),
                "error_type": local_err.__class__.__name__,
            })
            raise ModelCascadeError(
                f"All providers failed. Cloud error: {self.audit_log[0].get('error')}. Local error: {str(local_err)}"
            ) from local_err
