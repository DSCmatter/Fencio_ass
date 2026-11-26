# Production-grade design

## Short answer

No. This prototype is not production-grade. It is a lab harness with a rule-based
attacker, a simulated target, SQLite state and a single process. A production
system needs isolation, independent verification, durable scheduling, strict
authorization and human review.

## Multi-agent split

Split the loop into planner, attacker and judge agents with separate contexts and
separate permissions. The planner sees state summaries, not raw secrets. The
attacker never sees finding verdicts. The judge is a larger hosted model with a
fine-tuned classifier, and it must be independent of the attacker. A finding is
accepted only when the judge and a deterministic rule layer both agree, and an
independent replay succeeds. Cross-check with a second judge on high-severity
items.

## Target connectors

All connectors run sandboxed and rate-limited. HTTP, MCP and browser tools get
allow-lists, per-target budgets, request timeouts and no credentials from the
agent context. Each tool call is recorded with its exact request and response.
Untrusted content is passed as data, never as instructions. Tool outputs are
tagged and quarantined before they reach the planner.

## Jobs and storage

Replace SQLite with a durable job queue plus Postgres. Store assessments,
attacks, evidence, verdicts and judge decisions as versioned rows. Use row-level
security for multi-tenant isolation. Checkpoint after every step and support
resume. Secrets live in a managed vault, are scoped per session and never enter
model context. Audit logs are append-only and cover who authorized each run and
which target was in scope.

## Attack library and CI

Version the attack library. Each template has an ID, a category, an author and a
changelog. Seed a regression suite from confirmed findings and run it in CI on
every change. Track false positives over time with labeled ground truth. Alert on
drift in detection rate, attack success rate and judge agreement. Re-test on a
schedule and after every target change.

## Authorization and safety

Enforce scope before any request. Deny public or production targets by default.
Require written authorization and a time window per engagement. Apply safe-attack
guardrails: no real credentials, no destructive tool calls, no outbound
exfiltration, no third-party systems. Route high-severity findings to a human
before publication. Maintain an explicit false-positive budget and measure it.

## Severity and frameworks

Calibrate severity against asset value and exploitability, not just response
strings. Map findings to OWASP LLM Top 10 and keep the mapping in the report.
Track remediation state and re-test after fixes. Reporting should separate
observed behavior from inferred risk.

## What this lab demonstrates

The five required classes are exercised with real requests and exact evidence.
The loop adapts, switches tactics, confirms through replay and writes a
structured report. The evaluation separates a vulnerable target from a hardened
control. These are the transferable parts. Everything above is the work needed
before a real engagement.
