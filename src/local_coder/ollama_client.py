from __future__ import annotations

import json
import urllib.error
import urllib.request


class OllamaClient:
    def __init__(self, host: str, model: str, timeout: int = 120):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def get(self, path: str) -> dict:
        req = urllib.request.Request(self.host + path, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach Ollama at {self.host}: {exc}") from exc

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        payload = {"model": self.model, "messages": messages, "tools": tools, "stream": False}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.host + "/api/chat", data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach Ollama at {self.host}: {exc}") from exc
