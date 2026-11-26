"""Domain types for an assessment. These are the shape every module shares."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AttackCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    INDIRECT_INJECTION = "indirect_injection"
    SENSITIVE_INFO_DISCLOSURE = "sensitive_information_disclosure"
    TOOL_ABUSE = "tool_abuse"
    JAILBREAK = "jailbreak"
    MEMORY_POISONING = "memory_poisoning"
    DATA_EXFILTRATION = "data_exfiltration"


REQUIRED_CATEGORIES = (
    AttackCategory.PROMPT_INJECTION,
    AttackCategory.SYSTEM_PROMPT_EXTRACTION,
    AttackCategory.INDIRECT_INJECTION,
    AttackCategory.SENSITIVE_INFO_DISCLOSURE,
    AttackCategory.TOOL_ABUSE,
)


class CapabilityKind(str, Enum):
    LLM = "llm"
    WEB = "web"
    FILE = "file"
    MEMORY = "memory"
    DATABASE = "database"
    EXTERNAL_CONTENT = "external_content"
    TOOL = "tool"


class Verdict(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUSPICIOUS = "suspicious"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Capability(BaseModel):
    name: str
    kind: CapabilityKind
    description: str = ""


class TargetProfile(BaseModel):
    name: str
    base_url: str
    capabilities: list[Capability] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AttackRecord(BaseModel):
    id: str
    category: AttackCategory
    tactic: str
    payload: str
    response: str
    tool_trace: list[str] = Field(default_factory=list)
    verdict: Verdict = Verdict.PENDING
    confidence: float = 0.0
    evidence: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    confirmation_of: str | None = None


class EvidenceItem(BaseModel):
    id: str
    finding_id: str
    attack_id: str
    request: dict[str, Any]
    response: dict[str, Any]
    canary_hits: list[str] = Field(default_factory=list)
    note: str = ""


class Finding(BaseModel):
    id: str
    name: str
    category: AttackCategory
    severity: Severity
    description: str
    methodology: str
    impact: str
    remediation: str
    reproduction: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class PlannerDecision(BaseModel):
    step: int
    next_category: AttackCategory | None
    tactic: str
    rationale: str
    created_at: datetime = Field(default_factory=utcnow)


class AssessmentState(BaseModel):
    target: TargetProfile
    surface: list[Capability] = Field(default_factory=list)
    tested: list[AttackRecord] = Field(default_factory=list)
    confirmed: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)
    suspicious: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    queue: list[dict[str, Any]] = Field(default_factory=list)
    planner_log: list[PlannerDecision] = Field(default_factory=list)
    budgets: dict[str, int] = Field(default_factory=dict)
    step: int = 0
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None

    def attack_count(self, category: AttackCategory) -> int:
        return sum(1 for item in self.tested if item.category == category)
