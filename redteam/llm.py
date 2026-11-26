"""One generate interface for the attacker model. No model is loaded locally."""
from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from .config import Config
from . import offline_model


class LLMError(RuntimeError):
    """Raised when the model endpoint cannot produce a usable response."""


class LLMClient:
    def __init__(self, config: Config, backend: str | None = None) -> None:
        model = config.model
        self.model_name = model.model_name
        self.timeout_s = model.timeout_s
        self.max_retries = model.max_retries
        self.api_key = os.environ.get(model.api_key_env, "")
        requested = (backend or model.backend).strip().lower()
        if requested == "auto":
            explicit_endpoint = bool(os.environ.get("RT_MODEL_BASE_URL")) or bool(self.api_key)
            requested = "remote" if explicit_endpoint else "deterministic"
        if requested not in {"remote", "deterministic"}:
            raise ValueError(f"Unknown model backend: {requested}")
        self.backend = requested
        self.base_url = model.base_url.rstrip("/")
        self._http = httpx.Client(timeout=self.timeout_s) if requested == "remote" else None

    def describe(self) -> str:
        if self.backend == "remote":
            return f"remote:{self.model_name or 'unspecified'}"
        return "deterministic:rule-v1"

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return self.base_url + "/chat/completions"
        return self.base_url + "/v1/chat/completions"

    def generate(self, messages: list[dict[str, str]], **opts: Any) -> str:
        if self.backend == "deterministic":
            return offline_model.generate(messages)
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": float(opts.get("temperature", 0.4)),
            "max_tokens": int(opts.get("max_tokens", 1024)),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = self._endpoint()
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                assert self._http is not None
                response = self._http.post(url, json=payload, headers=headers)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        time.sleep(min(2 ** attempt, 8))
                        continue
                    raise LLMError(f"model endpoint returned HTTP {response.status_code}")
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"].get("content") or ""
                return str(content).strip()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise LLMError(f"malformed model response: {exc}") from exc
        raise LLMError(f"model request failed after {self.max_retries + 1} attempts: {last_error}")

    def generate_json(self, messages: list[dict[str, str]], **opts: Any) -> dict[str, Any]:
        text = self.generate(messages, **opts)
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            if self.backend == "deterministic":
                raise LLMError("deterministic backend produced invalid JSON")
            repair = list(messages) + [
                {
                    "role": "user",
                    "content": "Your previous reply was not valid JSON. Return only a single JSON object with the requested keys, no code fence and no prose.",
                }
            ]
            text = self.generate(repair, **opts)
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise LLMError("model produced invalid JSON after repair") from exc
        if not isinstance(value, dict):
            raise LLMError("model JSON response is not an object")
        return value

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
