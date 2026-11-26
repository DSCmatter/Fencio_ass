"""Payload generation seeded by templates and conditioned on past attempts."""
from __future__ import annotations

import json
from difflib import SequenceMatcher

from .attacks import library
from .llm import LLMClient
from .models import AssessmentState, AttackCategory


class Attacker:
    def __init__(self, llm: LLMClient, similarity_threshold: float = 0.9) -> None:
        self.llm = llm
        self.similarity_threshold = similarity_threshold

    def generate(
        self,
        state: AssessmentState,
        category: AttackCategory,
        tactic: str,
        attempt: int,
        confirmation_target: str | None = None,
    ) -> tuple[str, str]:
        prior = [item.payload for item in state.tested if item.category == category]
        context = {
            "category": category.value,
            "tactic": tactic,
            "attempt": attempt,
            "target_capabilities": [item.kind.value for item in state.surface],
            "prior_payloads": prior[-12:],
            "confirmation_target": confirmation_target,
        }
        messages = [
            {
                "role": "system",
                "content": "You generate one attack payload for an authorized local security assessment. Return only the payload text.",
            },
            {
                "role": "user",
                "content": "TASK: attack_generation\nCONTEXT: " + json.dumps(context, ensure_ascii=False),
            },
        ]
        payload = self.llm.generate(messages, temperature=0.6).strip()
        if not payload:
            raise RuntimeError("attacker produced an empty payload")
        if self._is_repeat(payload, prior):
            fallback = library.select_payload(category.value, tactic, attempt + 1, prior)
            payload = library.variant(fallback, attempt + 1)
        return payload, tactic

    def _is_repeat(self, payload: str, prior: list[str]) -> bool:
        return any(
            SequenceMatcher(None, payload, item).ratio() >= self.similarity_threshold for item in prior
        )
