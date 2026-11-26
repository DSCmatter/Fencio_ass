"""Reproduce suspected findings with an independent confirmation attack."""
from __future__ import annotations

from .analyzer import Analysis, Analyzer
from .attacker import Attacker
from .executor import ExecutionResult, Executor
from .models import AssessmentState, AttackCategory, Verdict


def verify(
    state: AssessmentState,
    original: ExecutionResult,
    analysis: Analysis,
    attacker: Attacker,
    executor: Executor,
    analyzer: Analyzer,
    max_followups: int,
) -> tuple[bool, Analysis | None, ExecutionResult | None]:
    if not analysis.vulnerable:
        return False, None, None
    prior_confirmations = sum(
        1 for item in state.tested if item.confirmation_of == original.record.id
    )
    if prior_confirmations >= max_followups:
        return False, None, None

    payload, tactic = attacker.generate(
        state,
        analysis.category,
        original.record.tactic + "_confirmation",
        attempt=prior_confirmations + 1,
        confirmation_target=original.record.id,
    )
    confirmation = executor.execute(payload, analysis.category, tactic, original.record.id)
    confirmed_analysis = analyzer.analyze(confirmation.record, analysis.category)
    if confirmed_analysis.vulnerable:
        confirmation.record.verdict = Verdict.CONFIRMED
        return True, confirmed_analysis, confirmation
    confirmation.record.verdict = Verdict.SUSPICIOUS
    return False, confirmed_analysis, confirmation
