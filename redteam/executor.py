"""Send attacks to the target, capture full traces, and host payload content locally."""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

from .models import AttackCategory, AttackRecord, utcnow
from .target_client import TargetClient

CONTENT_DIR = Path(__file__).parent / "attacks" / "content"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


class ContentServer:
    """Serves attacker-controlled pages on loopback for indirect injection tests."""

    def __init__(self) -> None:
        handler = partial(_QuietHandler, directory=str(CONTENT_DIR))
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/poisoned_page.html"

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@dataclass
class ExecutionResult:
    record: AttackRecord
    request: dict[str, Any]
    response: dict[str, Any]


class Executor:
    def __init__(self, client: TargetClient, content_server: ContentServer | None = None) -> None:
        self.client = client
        self.content = content_server or ContentServer()
        self.content.start()

    def execute(
        self,
        payload: str,
        category: AttackCategory,
        tactic: str,
        confirmation_of: str | None = None,
    ) -> ExecutionResult:
        rendered = payload.replace("{content_url}", self.content.url)
        result = self.client.chat(rendered)
        record = AttackRecord(
            id=f"atk-{uuid4().hex[:12]}",
            category=category,
            tactic=tactic,
            payload=rendered,
            response=str(result["text"]),
            tool_trace=list(result["tool_trace"]),
            created_at=utcnow(),
            confirmation_of=confirmation_of,
        )
        return ExecutionResult(record, result["request"], result["response"])

    def close(self) -> None:
        self.client.close()
        self.content.stop()
