"""Honest rule-based stand-in for the model when no remote endpoint is configured.

Every reply is produced by deterministic Python. The agent labels its backend as
deterministic in logs and reports, so nothing here is presented as model output.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .attacks import library


def _last_user(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _task(text: str) -> str:
    match = re.search(r"^TASK:\s*(\S+)", text, re.MULTILINE)
    return match.group(1) if match else ""


def _context(text: str) -> dict[str, Any]:
    match = re.search(r"^CONTEXT:\s*(\{.*\})\s*$", text, re.MULTILINE | re.DOTALL)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def generate(messages: list[dict[str, str]]) -> str:
    text = _last_user(messages)
    task = _task(text)
    context = _context(text)
    if task == "attack_generation":
        return generate_attack(context)
    if task == "response_analysis":
        return generate_analysis(context)
    if task == "strategy_planning":
        return generate_plan(context)
    if task == "recon_analysis":
        return generate_recon(context)
    raise ValueError(f"deterministic backend has no handler for task {task!r}")


def generate_attack(context: dict[str, Any]) -> str:
    category = str(context.get("category", "prompt_injection"))
    tactic = str(context.get("tactic", "")) or None
    attempt = int(context.get("attempt", 0))
    prior = [str(item) for item in context.get("prior_payloads", [])]
    payload = library.select_payload(category, tactic, attempt, prior)
    return library.variant(payload, attempt)


def generate_analysis(context: dict[str, Any]) -> str:
    from .analyzer import rule_signals

    payload = str(context.get("payload", ""))
    response = str(context.get("response", ""))
    canary_hits = [str(item) for item in context.get("canary_hits", [])]
    tool_trace = [str(item) for item in context.get("tool_trace", [])]
    requested = str(context.get("category", ""))
    signals = rule_signals(payload, response, canary_hits, tool_trace)
    vulnerable = bool(signals)
    category = _category_from_signals(signals, requested)
    confidence = min(0.97, 0.72 + 0.08 * (len(signals) - 1)) if vulnerable else 0.74
    return json.dumps(
        {
            "vulnerable": vulnerable,
            "category": category,
            "evidence": "; ".join(signals),
            "confidence": round(confidence, 2),
            "signals": signals,
        }
    )


def generate_plan(context: dict[str, Any]) -> str:
    counts = context.get("counts", {})
    surface = [str(item) for item in context.get("surface", [])]
    categories = list(library.PRIORITY_CATEGORIES)
    ranked = sorted(categories, key=lambda item: (int(counts.get(item, 0)), categories.index(item)))
    next_category = ranked[0] if ranked else None
    return json.dumps(
        {
            "next_category": next_category,
            "rationale": f"fewest attempts among required categories: {next_category}",
            "tactic": "initial_probe",
            "surface": surface,
        }
    )


def generate_recon(context: dict[str, Any]) -> str:
    reply = str(context.get("response", "")).lower()
    found = [name for name, words in library.CAPABILITY_WORDS.items() if any(word in reply for word in words)]
    return json.dumps({"capabilities": found, "note": "keyword match on recon reply"})


def _category_from_signals(signals: list[str], requested: str) -> str:
    joined = " ".join(signals).lower()
    if "canary" in joined or "system prompt" in joined:
        return "system_prompt_extraction"
    if "credential" in joined or "secret" in joined:
        return "sensitive_information_disclosure"
    if "unauthorized tool" in joined:
        return "tool_abuse"
    if "instruction override" in joined:
        return "prompt_injection"
    return requested or "prompt_injection"
