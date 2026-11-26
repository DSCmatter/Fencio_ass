# Decisions

This file records what was selected, what was built locally, and why.

## Environment deviations from PLAN.md

| Planned | Actual | Reason |
|---|---|---|
| Python 3.11 | Python 3.12.13 | 3.11 is not installed. A project-local `.venv` was created with the available 3.12 interpreter. Code targets 3.11+ syntax. |
| Repo folder `redteam-agent/` | Workspace root | The workspace root already holds `PLAN.md` and the assignment. It is used as the repo root to avoid duplicating those files. |

## Used vs. built

| Component | Source | Notes |
|---|---|---|
| Local runtime libraries (pydantic, httpx, FastAPI, Jinja2, Rich, PyYAML, datasets) | Third-party, free | Plumbing only. Installed from PyPI. |
| Base model Qwen2.5-3B-Instruct | Third-party, Apache-2.0 | Selected in PLAN.md. Used only on remote GPU. |
| Unsloth + TRL QLoRA | Third-party, free | Training code is a thin script; the recipe and dataset are ours. |
| DVAA target | Third-party, Apache-2.0 | Runs natively with `npm start`. No Docker. No fallback target needed. Canaries added locally. See `target/ARCHITECTURE.md`. |
| Agent loop, state machine, planner, attack generation logic, analyzer, verifier, severity, reporting, synthetic dataset, evaluation harness | Built here | Core offensive reasoning is our implementation, not a wrapper around garak, PyRIT, or promptfoo. |

## Later decisions

- The Hub push was optional and required an HF token. User chose to skip it. The
  adapter stays local and is copied to Drive. `docs/MODEL_CARD.md` is kept in the
  repo. No Hub URL or eval numbers are claimed.
- No credentials or endpoint existed locally, so `llm.py` uses a labeled
  `deterministic:rule-v1` offline backend. It is rule-based and never presented
  as the fine-tuned model. It switches to `remote` when the tunnel URL arrives.
- The real evaluation uses five CLI runs per target. LegacyBot ASR 0.5 with five
  of five classes found and zero false positives. SecureBot produced zero
  findings. Earlier status that claimed different numbers was wrong and was
  corrected against `eval/results/evaluation.json`.

## Rules held

- No model is loaded, trained, or served on the local machine.
- No paid service. No Docker.
- The only target is the local intentionally vulnerable app.
- Every reported number comes from a real run. Failures are recorded, not hidden.
