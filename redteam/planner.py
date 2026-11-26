"""Next-step decisions with logged rationale."""
from __future__ import annotations

from dataclasses import dataclass

from .attacks import library
from .models import AssessmentState, AttackCategory, PlannerDecision, utcnow


@dataclass
class Cursor:
    category_index: int = 0
    tactic_index: int = 0
    consecutive_failures: int = 0

    def observe(self, vulnerable: bool) -> None:
        self.consecutive_failures = 0 if vulnerable else self.consecutive_failures + 1


def _tactics(category: AttackCategory) -> list[str]:
    tactics: list[str] = []
    for template in library.load_templates(category.value):
        tactic = str(template.get("tactic", "unknown"))
        if tactic not in tactics:
            tactics.append(tactic)
    return tactics or ["initial_probe"]


def decide(
    state: AssessmentState,
    cursor: Cursor,
    budgets: dict[str, int],
    priority: list[AttackCategory],
) -> PlannerDecision | None:
    max_total = int(budgets.get("max_total_attacks", 60))
    max_per_category = int(budgets.get("max_attacks_per_category", 8))
    switch_after = int(budgets.get("switch_after_failures", 2))
    if len(state.tested) >= max_total:
        return None

    confirmed_categories = {finding.category for finding in state.findings}
    candidates = [item for item in priority if item not in confirmed_categories]
    if not candidates:
        return None

    switched = False
    if cursor.consecutive_failures >= switch_after:
        cursor.tactic_index += 1
        cursor.consecutive_failures = 0
        switched = True

    category = candidates[min(cursor.category_index, len(candidates) - 1)]
    while state.attack_count(category) >= max_per_category:
        cursor.category_index += 1
        if cursor.category_index >= len(candidates):
            return None
        category = candidates[cursor.category_index]
        cursor.tactic_index = 0
        switched = True

    tactics = _tactics(category)
    tactic = tactics[cursor.tactic_index % len(tactics)]
    if switched:
        rationale = (
            f"switched tactic to {tactic} for {category.value}: "
            f"{switch_after} consecutive failures or category budget reached"
        )
    else:
        rationale = (
            f"selected {category.value}/{tactic}: "
            f"{state.attack_count(category)} prior attempts, "
            f"{len(confirmed_categories)} categories already confirmed"
        )
    return PlannerDecision(
        step=state.step,
        next_category=category,
        tactic=tactic,
        rationale=rationale,
        created_at=utcnow(),
    )
