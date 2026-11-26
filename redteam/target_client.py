"""HTTP client for the local target. It records the exact request and response."""
from __future__ import annotations

from typing import Any

import httpx


class TargetClient:
    def __init__(self, base_url: str, timeout_s: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=timeout_s)

    def endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return self.base_url + "/chat/completions"
        return self.base_url + "/v1/chat/completions"

    def chat(self, message: str) -> dict[str, Any]:
        request = {"messages": [{"role": "user", "content": message}]}
        response = self._http.post(self.endpoint(), json=request)
        response.raise_for_status()
        payload = response.json()
        return {
            "request": request,
            "response": payload,
            "text": _extract_text(payload),
            "tool_trace": _extract_tool_trace(payload),
            "status_code": response.status_code,
        }

    def close(self) -> None:
        self._http.close()


def _extract_text(payload: Any) -> str:
    if isinstance(payload, dict):
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content", "") if isinstance(message, dict) else ""
            return str(content)
        for key in ("response", "answer", "content"):
            if key in payload:
                return str(payload[key])
    return str(payload)


def _extract_tool_trace(payload: Any) -> list[str]:
    trace: list[str] = []
    keys = {"tool_calls", "tools_used", "tool_trace", "actions", "tool_results"}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in keys:
                    trace.append(str(value))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return trace
