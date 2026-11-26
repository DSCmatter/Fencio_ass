# Technical design

## Architecture

```
configs/agent.yaml ──> redteam/config.py
                          │
                          v
                     orchestrator.py ──> recon.py ──> surface.py
                          │                              │
                          v                              v
                      planner.py  <──────────────── categories + capabilities
                          │
                          v
          attacker.py ──> executor.py ──> target_client.py ──> DVAA (:7003 / :7001)
                          │
                          v
                      analyzer.py ──> verifier.py ──> severity.py
                          │
                          v
              state.py (SQLite) ──> reporting/report.py ──> report.md / report.html
```

No component loads a model locally. `llm.py` has two backends. `remote` calls an
OpenAI-compatible endpoint over HTTP. `deterministic` delegates to
`offline_model.py`, a labeled rule-based adapter used when no endpoint exists.
The backend is explicit in config and in the generated report.

## Model selection and training

Base model: `Qwen2.5-3B-Instruct`. Public weight on Hugging Face. No gated
access. Instruction-tuned and small enough for a free T4 with 4-bit quantization.
Fallback in `configs/train.yaml` is the 1.5B variant for OOM recovery.

QLoRA parameters live in `configs/train.yaml`: 4-bit base, LoRA r=16, alpha=32,
dropout 0.05, all seven projection modules, two epochs, learning rate 2e-4,
max sequence 2048, seed 1337. `training/train_qlora.py` uses Unsloth and TRL
`SFTTrainer` and saves the adapter plus tokenizer locally. The adapter is copied
to Drive by the notebook. No Hub push. No token needed.

Dataset: 4485 chat records. Three tasks.

| Task | Output shape | Count |
| --- | --- | --- |
| attack_generation | plain payload | 2683 |
| response_analysis | JSON `{vulnerable, category, evidence, confidence}` | 1163 |
| strategy_planning | JSON `{next_category, rationale, tactic}` | 639 |

Train 3589, val 448, test 448. Four accepted licences. Gated, NC, GPL and
unknown-licence sets were skipped. See `data/DATASET_CARD.md`.

`training/evaluate_model.py` runs base versus tuned on 80 held-out test records.
It records JSON validity, exact field accuracy and latency to
`eval/results/model_eval.json`. That file only appears after a real GPU run.

## Agent design

`recon.py` sends benign questions and keyword-matches capability words.
`surface.py` maps capabilities to the five required attack categories.
`planner.py` enforces per-category and total budgets and switches tactic after
two consecutive failures. `attacker.py` conditions payloads on prior attempts
and rejects near-duplicates using difflib similarity. `executor.py` sends
requests and can serve a local poisoned page for indirect tests.
`analyzer.py` combines canary regexes, response markers and model judgment.
`verifier.py` replays an independently generated confirmation attack. Only a
confirmed replay becomes a finding. `severity.py` scores impact, exploitability,
reproducibility and value. `state.py` persists after every step so a crash can
resume.

The planner rationale for every decision is stored in `planner_log` and shown
in the console log. `redteam.cli replay` re-sends saved attacks for audit.

## Detection and verification

Canaries were added to the DVAA clone: system prompt, secret and file markers.
`analyzer.py` checks responses for those markers plus override and privilege
markers. Rule signals are combined with the model's `response_analysis` JSON.
A suspected finding is not final until a second, different payload reproduces it.

## Real results

Canonical assessment: `reports/20261126-090434/report.md`. Ten attacks, five
confirmed findings, all five required classes, 13 evidence items. All five
scored critical by the transparent rubric. Earlier run
`reports/20261126-090356/` shows failed attempts and a tactic switch.

Evaluation: `eval/results/evaluation.json`, five real runs per target.

| Target | ASR | TP | FP | FN | Detection | Mean attacks to first success |
| --- | --- | --- | --- | --- | --- | --- |
| LegacyBot :7003 | 0.5 | 5 | 0 | 0 | 1.0 | 6 |
| SecureBot :7001 | 0.0 | 0 | 0 | 0 | n/a | n/a |

## Limitations

- Small sample. Five runs per target.
- Rule-based attacker, not the fine-tuned model, until the tunnel is supplied.
- DVAA is a simulator. Its web tool does not fetch the hosted poisoned page, so
  indirect-injection success is recorded as instruction override and labeled as
  such in the report.
- All five findings scored critical. The rubric is transparent but not calibrated
  against production assets.
- No GPU result yet. Base-versus-tuned accuracy is unknown.
