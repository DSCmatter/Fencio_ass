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

- Fine-tuning has not run locally. No GPU on this machine.
- Base-versus-tuned metrics are unknown until `training/evaluate_model.py`
  executes in the notebook. Do not invent them.
- The offline deterministic backend used in local runs is rule-based, not this
  model.
- DVAA is a simulator. Its web tool does not fetch hosted pages.

## Evaluation

Pending GPU run. Results will be written to `eval/results/model_eval.json` by
`training/evaluate_model.py`. No numbers are claimed here yet.
