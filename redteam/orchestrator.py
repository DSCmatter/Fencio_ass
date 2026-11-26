"""Assemble the single-responsibility modules into one assessment loop."""
from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from rich.console import Console

from .analyzer import Analyzer, canary_hits
from .attacker import Attacker
from .config import load_config
from .executor import Executor
from .llm import LLMClient
from .models import (
    AssessmentState,
    AttackCategory,
    EvidenceItem,
    Finding,
    REQUIRED_CATEGORIES,
    Severity,
    TargetProfile,
    Verdict,
    utcnow,
)
from .planner import Cursor, decide
from .recon import run_recon
from .reporting.report import generate_report
from .severity import score
from .state import StateStore
from .surface import categories_for, describe, map_surface
from .target_client import TargetClient
from .verifier import verify

console = Console()

REMEDIATION = {
    AttackCategory.PROMPT_INJECTION: "Treat untrusted text as data. Enforce instruction hierarchy outside the prompt and validate tool calls against a policy.",
    AttackCategory.SYSTEM_PROMPT_EXTRACTION: "Keep secrets and system instructions out of model context. Apply output filters for canary-like markers.",
    AttackCategory.INDIRECT_INJECTION: "Strip active instructions from fetched content, isolate tool outputs, and require human approval for consequential actions.",
    AttackCategory.SENSITIVE_INFO_DISCLOSURE: "Remove credentials from agent context, scope secrets per session, and redact sensitive patterns in responses.",
    AttackCategory.TOOL_ABUSE: "Enforce least privilege, path allow-lists, and per-tool authorization checks with audit logging.",
    AttackCategory.JAILBREAK: "Use refusal training, input classification, and system-level policy checks rather than relying on prompt wording.",
    AttackCategory.MEMORY_POISONING: "Validate and quarantine memory writes, sign trusted memories, and re-evaluate stored instructions per session.",
    AttackCategory.DATA_EXFILTRATION: "Block outbound destinations, monitor tool chains, and require explicit authorization for data transfers.",
}

IMPACT_TEXT = {
    AttackCategory.PROMPT_INJECTION: "An attacker can redirect agent behavior and override intended instructions.",
    AttackCategory.SYSTEM_PROMPT_EXTRACTION: "Hidden instructions and embedded configuration are exposed to the caller.",
    AttackCategory.INDIRECT_INJECTION: "Untrusted content can control the agent without direct user interaction.",
    AttackCategory.SENSITIVE_INFO_DISCLOSURE: "Credentials, configuration, or other users' data are exposed.",
    AttackCategory.TOOL_ABUSE: "The agent performs actions beyond its granted authority.",
    AttackCategory.JAILBREAK: "Safety behavior is bypassed by role or persona manipulation.",
    AttackCategory.MEMORY_POISONING: "Persistent instructions survive across sessions and influence future users.",
    AttackCategory.DATA_EXFILTRATION: "Protected data can be moved to an attacker-controlled destination.",
}


class RunLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []

    def log(self, text: str, style: str | None = None) -> None:
        console.print(text, markup=False, style=style)
        self.lines.append(text)

    def flush(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def _finding_id(category: AttackCategory) -> str:
    return f"finding-{category.value}"


def _ordered_categories(state: AssessmentState) -> list[AttackCategory]:
    mapped = categories_for(state.surface)
    ordered = [item for item in mapped if item in REQUIRED_CATEGORIES]
    for category in REQUIRED_CATEGORIES:
        if category not in ordered:
            ordered.append(category)
    for category in (
        AttackCategory.MEMORY_POISONING,
        AttackCategory.DATA_EXFILTRATION,
        AttackCategory.JAILBREAK,
    ):
        if any(item.category == category for item in state.tested) and category not in ordered:
            ordered.append(category)
    return ordered


def run_assessment(args) -> int:
    config = load_config(args.config)
    if args.target:
        config.target.base_url = args.target
    if args.state_db:
        config.run.state_db = args.state_db
    random.seed(config.run.seed)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(config.run.output_dir) / timestamp
    logger = RunLogger(output_dir / "run.log")
    llm = LLMClient(config, backend=getattr(args, "backend", None))
    client = TargetClient(config.target.base_url)
    executor = Executor(client)
    attacker = Attacker(llm)
    analyzer = Analyzer(llm)
    store = StateStore(config.run.state_db)

    logger.log(f"Target: {config.target.name} ({config.target.base_url})", "bold cyan")
    logger.log("Starting Security Assessment...", "bold")
    logger.log(f"Attacker backend: {llm.describe()}", "dim")

    state = store.load() if args.resume else None
    if state is None:
        state = AssessmentState(
            target=TargetProfile(name=config.target.name, base_url=config.target.base_url),
            budgets=config.budgets.model_dump(),
        )
    else:
        logger.log(f"Resumed state at step {state.step}", "yellow")

    if not state.surface:
        profile, replies = run_recon(client, config.target.name, config.budgets.max_recon_questions)
        state.target = profile
        state.surface = map_surface(profile.capabilities)
        for reply in replies:
            logger.log(f"  recon: {reply['question']} -> {reply['text'][:110]}", "dim")
        logger.log("[+] Reconnaissance complete", "green")
        logger.log(f"Attack Surface: {describe(state.surface)}", "cyan")
    else:
        logger.log("[+] Reconnaissance restored from state", "green")

    cursor = Cursor()
    priority = _ordered_categories(state)
    confirmation_count = 0

    while True:
        decision = decide(state, cursor, state.budgets, priority)
        if decision is None or decision.next_category is None:
            break
        state.step += 1
        state.planner_log.append(decision)
        logger.log(f"Planner: {decision.rationale}", "dim")

        category = decision.next_category
        attempt = state.attack_count(category)
        payload, tactic = attacker.generate(state, category, decision.tactic, attempt)
        result = executor.execute(payload, category, tactic)
        analysis = analyzer.analyze(result.record, category)
        record = result.record
        record.verdict = analysis.verdict
        record.confidence = analysis.confidence
        record.evidence = analysis.evidence
        state.tested.append(record)
        store.append_attack(record)
        status = "SUCCESS" if analysis.vulnerable else "FAILED"
        logger.log(f"    Test {state.step:02d} [{category.value}/{tactic}] ........ {status}", "green" if analysis.vulnerable else "red")

        evidence = EvidenceItem(
            id=f"ev-{uuid4().hex[:10]}",
            finding_id=_finding_id(analysis.category),
            attack_id=record.id,
            request=result.request,
            response=result.response,
            canary_hits=canary_hits(record.response),
            note=analysis.evidence,
        )
        state.evidence.append(evidence)

        if analysis.vulnerable:
            logger.log(f"[!] Potential finding: {category.value} ({analysis.confidence:.2f})", "yellow")
            confirmed, confirmation_analysis, confirmation = verify(
                state,
                result,
                analysis,
                attacker,
                executor,
                analyzer,
                config.budgets.max_followups_per_finding,
            )
            if confirmation is not None:
                confirmation_record = confirmation.record
                state.tested.append(confirmation_record)
                store.append_attack(confirmation_record)
                state.evidence.append(
                    EvidenceItem(
                        id=f"ev-{uuid4().hex[:10]}",
                        finding_id=_finding_id(analysis.category),
                        attack_id=confirmation_record.id,
                        request=confirmation.request,
                        response=confirmation.response,
                        canary_hits=canary_hits(confirmation_record.response),
                        note=f"confirmation: {confirmation_analysis.evidence if confirmation_analysis else ''}",
                    )
                )
                confirmation_count += 1
                logger.log(f"    Confirmation ...... {'SUCCESS' if confirmed else 'FAILED'}", "green" if confirmed else "red")
            if confirmed and confirmation_analysis is not None:
                _record_finding(state, record, analysis, confirmation_analysis, confirmation)
                state.confirmed.append(record.id)
                priority = [item for item in priority if item != analysis.category]
                cursor.category_index = 0
                cursor.tactic_index = 0
                cursor.consecutive_failures = 0
                logger.log(f"[+] Vulnerability Confirmed: {analysis.category.value}", "bold green")
            else:
                state.suspicious.append(record.id)
        else:
            state.rejected.append(record.id)

        cursor.observe(analysis.vulnerable)
        store.save(state)

    state.finished_at = utcnow()
    store.save(state)
    markdown_path, html_path = generate_report(state, output_dir, llm.describe())
    counts = {severity.value: 0 for severity in Severity}
    for finding in state.findings:
        counts[finding.severity.value] += 1
    logger.log("Assessment Complete", "bold")
    logger.log(
        f"Critical: {counts['critical']}  High: {counts['high']}  Medium: {counts['medium']}  Low: {counts['low']}",
        "bold",
    )
    logger.log(f"Report generated: {markdown_path}", "cyan")
    logger.log(f"HTML report: {html_path}", "dim")
    logger.log(f"State database: {config.run.state_db}", "dim")
    logger.flush()
    executor.close()
    llm.close()
    return 0


def _record_finding(
    state: AssessmentState,
    record,
    analysis,
    confirmation_analysis,
    confirmation,
) -> None:
    category = analysis.category
    result = score(
        category,
        confirmation_analysis.signals or analysis.signals,
        confirmation_analysis.confidence,
        confirmed=True,
    )
    evidence_ids = [
        item.id for item in state.evidence if item.attack_id in {record.id, confirmation.record.id}
    ]
    reproduction = (
        f"POST {state.target.base_url}/v1/chat/completions\n"
        f'Body: {{"messages": [{{"role": "user", "content": <payload below>}}]}}\n'
        f"Payload:\n{record.payload}\n"
        f"Expected: target refuses or isolates the request.\n"
        f"Observed: {record.response[:600]}"
    )
    state.findings.append(
        Finding(
            id=_finding_id(category),
            name=f"{category.value.replace('_', ' ').title()} confirmed on {state.target.name}",
            category=category,
            severity=result.severity,
            description=f"{IMPACT_TEXT.get(category, 'Security control bypass observed.')} {result.rationale}",
            methodology=(
                f"Seeded {record.tactic} template, model-conditioned variant, then an independent "
                f"confirmation replay ({confirmation.record.tactic})."
                + (
                    " Target limitation: LegacyBot's simulated web tool does not fetch the hosted page. "
                    "The observed success comes from instruction markers in the user turn wrapped around "
                    "the hosted-content request, so this is an instruction-override finding, not proof of "
                    "content-borne injection."
                    if category == AttackCategory.INDIRECT_INJECTION
                    else ""
                )
            ),
            impact=IMPACT_TEXT.get(category, "Unauthorized behavior confirmed."),
            remediation=REMEDIATION.get(category, "Apply least privilege and output validation."),
            reproduction=reproduction,
            evidence_ids=evidence_ids,
            confidence=confirmation_analysis.confidence,
        )
    )


def replay_attacks(args) -> int:
    config = load_config()
    store = StateStore(args.state_db)
    attacks = store.load_attacks()
    state = store.load()
    base_url = state.target.base_url if state else config.target.base_url
    client = TargetClient(base_url)
    results = []
    for attack in attacks:
        current = client.chat(attack.payload)
        hits = canary_hits(str(current["text"]))
        reproduced = bool(hits) or bool(current["tool_trace"])
        results.append(
            {
                "attack_id": attack.id,
                "category": attack.category.value,
                "original_response": attack.response[:300],
                "replay_response": str(current["text"])[:300],
                "canary_hits": hits,
                "reproduced": reproduced,
            }
        )
    output = Path(config.run.output_dir) / f"replay-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    reproduced = sum(1 for item in results if item["reproduced"])
    console.print(f"Replayed {len(results)} attacks; {reproduced} reproduced evidence markers.")
    console.print(f"Results: {output}")
    client.close()
    return 0
