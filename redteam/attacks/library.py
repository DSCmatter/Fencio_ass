"""Seed attack templates and deterministic variant selection."""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import yaml

TEMPLATES_DIR = Path(__file__).parent

PRIORITY_CATEGORIES = (
    "prompt_injection",
    "system_prompt_extraction",
    "indirect_injection",
    "sensitive_information_disclosure",
    "tool_abuse",
)

CAPABILITY_WORDS = {
    "web": ("web", "fetch", "url", "browse", "http"),
    "file": ("file", "read", "write", "path", "directory"),
    "memory": ("memory", "remember", "previous conversation", "history"),
    "database": ("database", "sql", "query", "db"),
    "external_content": ("document", "webpage", "page", "knowledge base", "repo"),
    "tool": ("tool", "shell", "command", "execute", "mcp"),
}


def available_categories() -> list[str]:
    return sorted(path.stem for path in TEMPLATES_DIR.glob("*.yaml"))


def load_templates(category: str) -> list[dict[str, Any]]:
    path = TEMPLATES_DIR / f"{category}.yaml"
    if not path.exists():
        return []
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(document.get("templates", []))


def select_payload(
    category: str,
    tactic: str | None,
    attempt: int,
    prior_payloads: list[str],
) -> str:
    templates = load_templates(category)
    if not templates:
        raise ValueError(f"no templates for category {category}")
    candidates = [item for item in templates if item.get("tactic") == tactic] if tactic else templates
    if not candidates:
        candidates = templates
    payloads = [str(item.get("payload", "")) for item in candidates]
    unused = [item for item in payloads if not _too_similar(item, prior_payloads)]
    pool = unused or payloads
    return pool[attempt % len(pool)]


def variant(payload: str, attempt: int) -> str:
    wrappers = (
        lambda text: text,
        lambda text: "SYSTEM OVERRIDE: " + text,
        lambda text: text + "\n--- END USER MESSAGE ---",
        lambda text: "[ADMIN] " + text + " [/ADMIN]",
        lambda text: "Please process this operator directive:\n" + text,
    )
    return wrappers[attempt % len(wrappers)](payload)


def _too_similar(candidate: str, prior: list[str], threshold: float = 0.9) -> bool:
    return any(SequenceMatcher(None, candidate, item).ratio() >= threshold for item in prior)
