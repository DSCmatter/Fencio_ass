# Model card

## Model

Base: `Qwen2.5-3B-Instruct`. Public on Hugging Face. No gated access.
Adapter: LoRA, saved locally to `checkpoints/qlora-adapter` by
`training/train_qlora.py`. Not pushed to the Hub by user decision.

## Why this base

Small enough for a free T4 with 4-bit quantization. Instruction-tuned, so chat
format and JSON tasks need little adaptation. Public licence and weights. The
1.5B variant in `configs/train.yaml` is the fallback if the T4 runs out of memory.

## Training data

4485 chat records in three task formats. Four accepted dataset licences are
documented in `data/DATASET_CARD.md`. Gated, non-commercial, GPL and
unknown-licence sets were excluded. Synthetic examples cover indirect injection,
tool abuse, system prompt extraction, data exfiltration and memory poisoning.
Train 3589, val 448, test 448. The test split is held out.

## Hyperparameters

4-bit base. LoRA r=16, alpha=32, dropout 0.05. Target modules q, k, v, o, gate,
up and down projections. Two epochs. Learning rate 2e-4. Batch 2 with gradient
accumulation 4. Max sequence length 2048. Warmup 0.03. Seed 1337. Checkpoint
every 50 steps. Values are in `configs/train.yaml`.

## Intended use

An offensive attacker model for authorized red teaming of a local, intentionally
vulnerable agent. Not for production use. Not for public targets.

## Limitations

- Fine-tuning ran on a free Colab T4, not locally. No GPU on this machine.
- The offline deterministic backend used in some local runs is rule-based, not
  this model. The tuned remote run is labeled `remote:qwen2.5-3b-qlora`.
- DVAA is a simulator. Its web tool does not fetch hosted pages.
- The evaluation sample is 80 held-out response-analysis records. Small sample.
- `mean_confidence_error` on the tuned model is near zero. This is the raw
  printed value. It may reflect overconfident or templated confidence outputs,
  not calibrated uncertainty.

## Evaluation

Real base-versus-tuned comparison on 80 held-out response-analysis records from
`data/processed/test.jsonl`. Run on a free Colab Tesla T4 with
`training/evaluate_model.py`. Source output was pasted from the Colab run and
saved to `eval/results/model_eval.json`.

| Metric | Base | Tuned |
| --- | --- | --- |
| JSON valid rate | 0.9875 (79/80) | 1.0 (80/80) |
| Vulnerable accuracy | 0.6875 | 1.0 |
| Category accuracy | 0.0 | 0.95 |
| Mean confidence error | 0.08139 | 0.00050 |
| Mean latency (s) | 3.413 | 5.491 |

The tuned adapter also drove the real remote assessment. Ten attacks, five
confirmed findings, all five required classes. Report
`reports/20261126-124641/report.md`.
