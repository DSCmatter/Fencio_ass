# AI Agent Red Teaming System

An autonomous red team agent that attacks an intentionally vulnerable local AI
agent, adapts its strategy, records evidence and emits a structured security
report.

## Safety

Authorized targets only. This tool attacks a local DVAA instance you control.
Do not point it at public or production systems. No credentials or secrets are
placed in model context. No model is loaded on this machine.

## Status

Phases 1 to 11 of `PLAN.md` are complete in code and verified locally. GPU
training, tuned serving and the base-versus-tuned comparison require a free
Colab or Kaggle run. Hub push was skipped by user decision.

## Layout

- `configs/` - agent and training configuration
- `data/` - dataset preparation and dataset card with licences
- `training/` - dataset prep, QLoRA training, evaluate, notebook, tunnel server
- `target/` - DVAA clone and its architecture document
- `redteam/` - agent loop, state, planner, attacker, analyzer, verifier, reports
- `eval/` - ground truth, evaluation harness and real results
- `reports/` - generated assessments and SQLite state
- `docs/` - technical notes, decisions, production design, model card, demo

## Local quickstart

Python 3.12 venv. PowerShell.

```powershell
C:\Users\Nyx\.local\bin\python3.12.exe -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m redteam.cli --version
python -m redteam.cli --help
```

Start the vulnerable target from a second terminal.

```powershell
cd d:\Coding\Fencio_ass\target\dvaa
npm start
```

LegacyBot listens on `http://127.0.0.1:7003`. SecureBot, the negative control,
listens on `http://127.0.0.1:7001`. Dashboard on `:9000`.

Run an assessment with the labeled offline backend.

```powershell
cd d:\Coding\Fencio_ass
python -m redteam.cli run --backend deterministic --state-db reports/state/assessment.db
```

Outputs go to `reports/<timestamp>/report.md`, `report.html` and `run.log`.
Replay saved attacks with `python -m redteam.cli replay`.

Run the evaluation against both targets.

```powershell
python -m eval.run_eval --runs 5
python -m redteam.cli eval --runs 5
```

Results land in `eval/results/evaluation.json`. See `docs/TECHNICAL.md`.

## Training on a free GPU

1. Publish this project or switch the notebook clone cell to a zip upload.
2. Open `training/notebook.ipynb` in Colab or Kaggle.
3. Runtime, change runtime type, T4 GPU, save.
4. Run all cells. The notebook trains on the T4, saves the adapter to Drive and
   evaluates base versus tuned into `eval/results/model_eval.json`.
5. The last cell prints `TUNNEL_URL=<url>/v1`. Paste that into `configs/agent.yaml`
   as `model.base_url`, or export `RT_MODEL_BASE_URL`.

No HF token is needed. Qwen2.5-3B-Instruct is public.

Run the tuned assessment.

```powershell
python -m redteam.cli run --backend remote
```

## Free tier notes

No Docker. No paid services. No local model loading. Only CPU work happens on
this machine. Unsloth, training and serving run on Colab or Kaggle. Datasets are
public and ungated with accepted licences.

## Documentation

- `docs/TECHNICAL.md` - architecture, data, agent design, real results
- `docs/PRODUCTION.md` - answer to the production-grade question
- `docs/DECISIONS.md` - choices and environment deviations
- `docs/MODEL_CARD.md` - model, data, hyperparameters, limitations
- `docs/DEMO_SCRIPT.md` - 12 minute recording script
- `target/ARCHITECTURE.md` - target surface and canaries
- `data/DATASET_CARD.md` - licences and dataset structure
