"""Turn recon observations into a ranked attack surface."""
from __future__ import annotations

from .models import AttackCategory, Capability, CapabilityKind

CATEGORY_BY_CAPABILITY: dict[CapabilityKind, tuple[AttackCategory, ...]] = {
    CapabilityKind.LLM: (
        AttackCategory.PROMPT_INJECTION,
        AttackCategory.SYSTEM_PROMPT_EXTRACTION,
        AttackCategory.SENSITIVE_INFO_DISCLOSURE,
    ),
    CapabilityKind.EXTERNAL_CONTENT: (AttackCategory.INDIRECT_INJECTION,),
    CapabilityKind.WEB: (AttackCategory.INDIRECT_INJECTION, AttackCategory.SENSITIVE_INFO_DISCLOSURE),
    CapabilityKind.FILE: (AttackCategory.TOOL_ABUSE, AttackCategory.SENSITIVE_INFO_DISCLOSURE),
    CapabilityKind.MEMORY: (AttackCategory.INDIRECT_INJECTION,),
    CapabilityKind.DATABASE: (AttackCategory.SENSITIVE_INFO_DISCLOSURE, AttackCategory.TOOL_ABUSE),
    CapabilityKind.TOOL: (AttackCategory.TOOL_ABUSE,),
}

RANK = {
    CapabilityKind.LLM: 0,
    CapabilityKind.EXTERNAL_CONTENT: 1,
    CapabilityKind.WEB: 2,
    CapabilityKind.FILE: 3,
    CapabilityKind.MEMORY: 4,
    CapabilityKind.DATABASE: 5,
    CapabilityKind.TOOL: 6,
}


def map_surface(capabilities: list[Capability]) -> list[Capability]:
    return sorted(capabilities, key=lambda item: RANK.get(item.kind, 99))


def categories_for(capabilities: list[Capability]) -> list[AttackCategory]:
    found: list[AttackCategory] = []
    for capability in capabilities:
        for category in CATEGORY_BY_CAPABILITY.get(capability.kind, ()):
            if category not in found:
                found.append(category)
    return found


def describe(surface: list[Capability]) -> str:
    return " | ".join(item.kind.value for item in surface)
