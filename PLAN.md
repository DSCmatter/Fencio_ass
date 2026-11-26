# PLAN.md: AI Agent Red Teaming System (Free-Tier Build)

You are an AI coding agent. Build the project below phase by phase. Follow the rules, finish each phase's acceptance criteria before moving on, and tick the checkboxes as you go.

## 0. Rules of Engagement

1. **Zero cost.** Use only free tiers (Kaggle/Colab GPU, Hugging Face Hub, free LLM APIs, GitHub). Never add a paid service.
2. **No Docker.** Run the target natively or use the fallback target (Phase 2).
3. **Authorized targets only.** Attack only the local intentionally vulnerable target. Never point the attacker at any public or production system.
4. **No fabricated results.** Every number, finding, and log in docs and reports must come from a real run. If something fails, record it honestly.
5. **Own the core logic.** Do not wrap an existing red-teaming framework (garak, PyRIT, promptfoo, etc.). Third-party libraries are fine for plumbing (HTTP, DB, templating, training).
6. **Document as you go.** Keep `docs/DECISIONS.md` updated with what you used vs. what you built.
7. **Ask the human** when blocked on credentials, GPU access, or licensing questions. Do not guess.
8. **No local models.** The human's machine has only a GTX 1650 (4 GB VRAM). Never load, train, or run any model locally. All training and model inference happen on Kaggle/Colab or via free hosted APIs. Local code is limited to lightweight Python (agent loop, HTTP calls, SQLite, reports) and the target app.

## 1. Fixed Decisions

| Area | Choice |
|---|---|
| Language | Python 3.11 |
| Base model | Qwen2.5-3B-Instruct (fall back to 1.5B if out of memory) |
| Fine-tuning | QLoRA via Unsloth + TRL, on Kaggle or Colab free GPU |
| Model hosting | LoRA adapter on Hugging Face Hub. Inference runs **remotely** in a Kaggle/Colab notebook, exposed as an OpenAI-compatible FastAPI endpoint through a free cloudflared tunnel. The local agent only makes HTTP calls. |
| Target | Damn Vulnerable AI Agent (`github.com/opena2a-org/damn-vulnerable-ai-agent`), run natively. Fallback: custom FastAPI target |
| Target's own LLM (if needed) | Free API tier (Groq, Gemini, or OpenRouter free models) |
| State | Pydantic models, persisted in SQLite |
| HTTP | `httpx` |
| Console log | Rich |
| Reports | Jinja2, to Markdown and HTML |
| Eval | Custom harness (attack success rate, false positives, false negatives) |

## 2. Repository Layout

```
redteam-agent/
├── README.md
├── PLAN.md
├── pyproject.toml / requirements.txt
├── configs/
│   ├── agent.yaml            # model endpoint, target URL, limits
│   └── train.yaml            # hyperparameters
├── data/
│   ├── raw/                  # downloaded public datasets (untouched)
│   ├── processed/            # train.jsonl, val.jsonl, test.jsonl
│   └── DATASET_CARD.md       # sources, licenses, structure
├── training/
│   ├── prepare_dataset.py
│   ├── train_qlora.py
│   ├── evaluate_model.py
│   └── notebook.ipynb        # Kaggle/Colab runner
├── target/
│   ├── dvaa/                 # cloned target (gitignored or submodule)
│   ├── fallback_target/      # FastAPI vulnerable agent (if needed)
│   └── ARCHITECTURE.md       # target architecture + attack surface
├── redteam/
│   ├── llm.py                # model client (adapter or API)
│   ├── state.py              # Pydantic assessment state + SQLite persistence
│   ├── recon.py
│   ├── surface.py            # attack surface identification
│   ├── planner.py            # strategy planning, next-attack decision
│   ├── attacker.py           # attack generation (fine-tuned model)
│   ├── executor.py           # sends attacks to target, records traces
│   ├── analyzer.py           # response analysis
│   ├── verifier.py           # confirm/reject findings
│   ├── severity.py
│   ├── attacks/              # seed templates per category
│   ├── reporting/
│   │   ├── report.py
│   │   └── templates/report.md.j2
│   └── cli.py                # `python -m redteam.cli run --target URL`
├── eval/
│   ├── ground_truth.yaml
│   ├── run_eval.py
│   └── results/
├── reports/                  # generated assessment outputs
├── docs/
│   ├── TECHNICAL.md
│   ├── DECISIONS.md
│   └── PRODUCTION.md         # answer to the final question
└── tests/
```

## Phase 1: Project Setup

- [x] Create the repo, venv, `requirements.txt`, `.gitignore` (ignore secrets, checkpoints, `data/raw`).
- [x] Add `configs/agent.yaml` with placeholders for model endpoint, target URL, max attacks per category, max follow-ups.
- [x] Load secrets from environment variables only. Add `.env.example`.

**Acceptance:** `python -m redteam.cli --help` runs.

## Phase 2: Target Setup and Architecture Doc

The assignment requires the target architecture to be documented **before** testing.

- [x] Clone DVAA. Read its README, install dependencies, run it natively on `localhost`.
- [x] If it cannot run in this environment, build `target/fallback_target/` with FastAPI: an LLM-backed chat endpoint with a hidden system prompt containing a canary secret, a file-read tool, a web-fetch tool, a memory store, a fake database tool, and one tool that is deliberately over-privileged. Keep a documented ground truth of which vulnerabilities exist.
  - skip: DVAA runs natively on Node 26 without Docker or credentials, so the fallback target was not needed.
- [x] Write `target/ARCHITECTURE.md`: components, endpoints, tools, data flows, trust boundaries, and an attack-surface table mapped to the five minimum vulnerability classes.
- [x] Plant canary strings (e.g. `CANARY-SYSPROMPT-xxxx`, `CANARY-SECRET-xxxx`) in the system prompt, files, and data so verification can be rule-based.

**Acceptance:** A manual `curl` to the target returns a response. `ARCHITECTURE.md` exists and lists the attack surface.

## Phase 3: Dataset

- [x] Download public datasets into `data/raw/` (suggested: `deepset/prompt-injections`, JailbreakBench behaviors/artifacts, other open prompt-injection sets). **Verify each license** and record it in `data/DATASET_CARD.md`. Skip anything with unclear or restrictive licensing.
- [x] Write `prepare_dataset.py` to build chat-format JSONL with three task types:
  1. **Attack generation:** input is category + target capabilities + prior attempts; output is the next attack payload.
  2. **Response analysis:** input is attack + target response; output is JSON `{vulnerable: bool, category, evidence, confidence}`.
  3. **Strategy planning:** input is assessment state summary; output is JSON `{next_category, rationale, tactic}`.
- [x] Add synthetic examples (hand-written seeds plus template expansion) for categories the public sets lack: indirect injection, tool abuse, system prompt extraction, data exfiltration, memory poisoning. Mark them `source: synthetic`.
- [x] Split train/val/test (e.g. 80/10/10), de-duplicated, with the test split held out.
- [x] Document the dataset structure with one example per task in `DATASET_CARD.md`.

**Acceptance:** `train.jsonl`, `val.jsonl`, `test.jsonl` exist, with at least ~2,000 training examples across all three tasks.

## Phase 4: Fine-Tuning

- [x] Write `train_qlora.py` (Unsloth + TRL SFTTrainer): 4-bit base, LoRA r=16, alpha=32, target all linear projection layers, 1-3 epochs, learning rate ~2e-4, max seq length 2048. Put all values in `configs/train.yaml`.
- [x] Write `notebook.ipynb` that clones the repo, installs dependencies, trains on Kaggle/Colab, and saves checkpoints regularly (sessions disconnect).
- [x] Write `training/serve_notebook.py` (or a notebook cell) that loads the base model plus adapter on the remote GPU, serves `/v1/chat/completions` with FastAPI, and opens a cloudflared tunnel. Print the tunnel URL so the human can paste it into `configs/agent.yaml`. If the tunnel is unreliable, fall back to running the whole agent inside the notebook.
- [x] Push the adapter to the HF Hub with a model card (base model, why chosen, data, hyperparameters, limitations). **SKIPPED.** Public Hub push is optional and needs an HF token. The adapter is saved locally and copied to Drive. Model card is kept in the repo. No token required to download Qwen2.5-3B-Instruct.
- [x] Write `evaluate_model.py`: on the test split, measure JSON validity rate, analysis accuracy (vulnerable vs. not), and compare the **base model vs. fine-tuned model**. Save to `eval/results/model_eval.json`.

**Acceptance:** Code complete and locally verified. GPU training, local adapter save, and base-vs-tuned numbers require the user's free Colab/Kaggle run. Hub push skipped by user decision. No numbers fabricated.

## Phase 5: Red Team Agent Core

Build the loop in this order. Each module has a single responsibility.

- [x] **`llm.py`**: one `generate(messages, **opts)` interface. HTTP only (OpenAI-compatible endpoint from the remote notebook tunnel, or a free API such as Groq/Gemini/OpenRouter as a fallback). No local model loading. Retry, timeout, and rate-limit backoff handling. The no-credential path uses a labeled deterministic rule backend (`offline_model.py`), not a local model.
- [x] **`state.py`**: Pydantic `AssessmentState` holding target profile, attack surface, `tested` (attack, category, response, verdict), `confirmed`, `rejected`, `suspicious`, `queue`, `evidence`, and budgets. Persist to SQLite after every step so a crash can resume.
- [x] **`recon.py`**: probe the target with benign questions ("what can you do?", "what tools do you have?"), parse the answers into a capability profile.
- [x] **`surface.py`**: map the capability profile to attack classes (LLM, web tool, file tool, memory, DB, external content). Output a ranked list.
- [x] **`attacker.py`**: generate payloads using the fine-tuned model, seeded by templates in `attacks/` and conditioned on past results. Must produce a *different* attack when the previous one failed (track and avoid repeats via similarity check).
- [x] **`executor.py`**: send the payload to the target, capture the full request, response, and any tool-call traces. For indirect injection, host attacker-controlled content (a local page or file) and ask the target to process it.
- [x] **`analyzer.py`**: classify each response. Combine rule checks (canary leaked, unauthorized tool call, instruction-following markers) with the model's judgment. Output verdict and confidence.
- [x] **`planner.py`**: decide the next step from state: escalate a promising lead, switch tactic after N failures, move to the next category, or stop. Log the rationale.
- [x] **`verifier.py`**: for every suspected finding, run a **confirmation attack** (a variant or replay). Confirm only if it reproduces. Otherwise mark as rejected or suspicious.
- [x] **`severity.py`**: transparent scoring (e.g. impact x exploitability x reproducibility), mapped to Critical/High/Medium/Low.

**Acceptance:** Running the agent on the target performs recon, tests at least one category end to end, and writes state to SQLite.

## Phase 6: Attack Coverage

Implement all five required classes with seed templates plus model-generated variants:

- [x] Prompt injection (instruction override, role confusion, delimiter attacks)
- [x] System prompt extraction (direct, paraphrase, translation, "repeat above" tricks)
- [x] Indirect prompt injection (poisoned webpage or document, hidden instructions)
- [x] Sensitive information disclosure (secrets, other users' data, config)
- [x] Tool abuse / excessive agency (unauthorized file read, over-privileged tool calls, path traversal against the target's own sandbox)

Bonus, in priority order (cheap first):

- [ ] Multi-turn attack chains
- [ ] Memory poisoning (templates exist; no live finding against LegacyBot)
- [x] Attack replay from SQLite history
- [x] Severity scoring (already in Phase 5)
- [ ] Tool authorization testing
- [ ] RAG security testing (if the target has RAG)

**Acceptance:** Each class has at least 3 distinct attack strategies, and the agent switches strategies on failure (visible in logs).

## Phase 7: Runtime Output

Use Rich to print a live log in this style:

```
Target: <name>
Starting Security Assessment...
[+] Reconnaissance complete
Attack Surface: LLM | Web Tool | File Tool | Memory
[+] Starting Prompt Injection Tests
    Test 01 ........ FAILED
    Test 02 ........ SUCCESS
[!] Potential Prompt Injection Found
[+] Generating follow-up attack...
    Follow-up ...... SUCCESS
[+] Vulnerability Confirmed
Assessment Complete
Critical: n  High: n  Medium: n  Low: n
Report generated: reports/<timestamp>/report.md
```

- [x] Show the planner's rationale for each strategy switch.
- [x] Write a plain-text copy of the log to `reports/<timestamp>/run.log`.

**Acceptance:** The log is readable and matches the actual state in SQLite.

## Phase 8: Report Generation

- [x] Jinja2 template with: **Executive Summary** (overall posture, counts by severity, methodology in 3-4 lines) and a **Findings** section.
- [x] Each finding includes: name, severity, description, attack category, attack methodology, evidence (exact request and response excerpts), target response, impact, reproduction steps (copy-pasteable payload and expected result), and remediation.
- [x] Also include rejected or suspicious items in an appendix, plus run metadata (model, adapter version, target, budgets, timestamps).
- [x] Output Markdown and HTML.

**Acceptance:** A real report is generated from a real run against the target.

## Phase 9: Evaluation

- [x] Write `eval/ground_truth.yaml` listing which vulnerabilities truly exist on the target (the fallback target makes this exact; for DVAA, base it on its documented challenges).
- [x] `run_eval.py` runs the agent N times (e.g. 5) and computes per-class attack success rate, true positives, **false positives**, **false negatives**, and mean attacks-to-first-success.
- [x] Optional: run with the base model vs. the fine-tuned model and compare. **PENDING GPU.** `training/evaluate_model.py` is written and runs in the notebook. Comparison blocked on the user's Colab/Kaggle run.
- [x] Save results to `eval/results/` and summarize in `docs/TECHNICAL.md`. Report limits honestly (small sample, small model).

**Acceptance:** `eval/results/evaluation.json` produced by 5 real runs per target. LegacyBot ASR 0.5, detection 5/5, FP 0, FN 0, mean 6 attacks to first success. SecureBot ASR 0, FP 0. Model comparison pending GPU.

## Phase 10: Documentation

- [x] `README.md`: what it is, quickstart, reproduction steps for training and for the assessment, free-tier notes, and a safety note (authorized targets only).
- [x] `docs/TECHNICAL.md`: architecture diagram, model selection rationale, training process, agent design, attack methodology, detection/verification methodology, limitations.
- [x] `docs/DECISIONS.md`: a "used vs. built" table (third-party: Unsloth, TRL, HF datasets, DVAA, etc.; own work: agent loop, planner, verifier, severity, reporting, synthetic data).
- [x] `docs/PRODUCTION.md`: answer to the final question. Covers multi-agent split, hosted judge, sandboxed connectors, durable queue and Postgres, versioned attack library with CI, authorization and audit logs, tenant isolation and secrets, human review, severity calibration, OWASP mapping, drift monitoring and safe-attack guardrails.

**Acceptance:** README reproduces local setup, assessment, evaluation and the GPU path. Model card in `docs/MODEL_CARD.md`.

## Phase 11: Demo Preparation (10-15 min)

- [x] Write `docs/DEMO_SCRIPT.md` with timings: intro (1 min), target architecture (2 min), model and training summary (2 min), **live assessment run** (6-8 min), report walkthrough (2 min), eval results and production thoughts (1-2 min).
- [x] The live run shows real activity: recon, a failed attempt from `reports/20261126-090356/run.log`, a strategy switch, a confirmation step.
- [x] The script tells the human to keep target and agent loaded, do a dry run, and record the video. The agent cannot record video itself.

## Final Checklist

- [x] Repo runs end to end from the README. Local path verified.
- [x] Adapter on HF Hub with model card. **SKIPPED** by user decision. Local adapter and `docs/MODEL_CARD.md` instead.
- [x] Dataset and `DATASET_CARD.md` with licenses
- [x] Target `ARCHITECTURE.md` written before testing
- [x] All 5 vulnerability classes covered
- [x] Adaptive loop with persisted state, strategy switching, and verification
- [x] Real generated report in `reports/`
- [x] Eval metrics (ASR, FP, FN) from real runs
- [x] `TECHNICAL.md`, `DECISIONS.md`, `PRODUCTION.md` complete
- [x] Demo script ready
- [x] GPU training, base-vs-tuned eval and tuned remote assessment. Real Colab T4 run. Report `reports/20261126-124641/report.md`.
- [ ] Demo video. Manual. User records.

## Failure Playbook

- **GPU out of memory:** drop to Qwen2.5-1.5B, reduce max seq length, lower batch size, enable gradient checkpointing.
- **Session disconnects:** checkpoint to Drive/Hub every N steps. Resume from SQLite state.
- **DVAA won't run:** switch to the fallback target and note why in `DECISIONS.md`.
- **Model output is invalid JSON:** constrain output, retry with a repair prompt, and fall back to rule-based analysis.
- **Free API rate limits:** add backoff, cache responses, and reduce parallelism.