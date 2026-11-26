# Demo script, 12 minutes

Record your screen. The agent cannot record video. Keep DVAA and the agent
loaded in one session. Do a dry run first.

## 0:00 to 1:00. Intro

Show `README.md`. Say what the system is. An autonomous red team agent against
a local, intentionally vulnerable target. No public systems. No local model
loaded on this machine.

## 1:00 to 2:00. Target architecture

Open `target/ARCHITECTURE.md`. Show LegacyBot on :7003, SecureBot on :7001 and
the dashboard on :9000. Point at the canary markers in the clone. Explain the
five required classes.

## 2:00 to 3:00. Model and training

Open `training/notebook.ipynb` and `configs/train.yaml`. Show 4485 records,
three tasks, Qwen2.5-3B, 4-bit LoRA r=16. State honestly that the local demo
uses the labeled deterministic backend because the GPU run has not happened.

## 3:00 to 9:00. Live assessment

Start DVAA if needed.

```powershell
cd d:\Coding\Fencio_ass\target\dvaa
npm start
```

In a second terminal:

```powershell
& d:\Coding\Fencio_ass\.venv\Scripts\Activate.ps1
cd d:\Coding\Fencio_ass
python -m redteam.cli run --backend deterministic --state-db reports/state/demo.db
```

Show the console. Narrate four moments.

- Reconnaissance. Capability list appears.
- A failed attempt. Use `reports/20261126-090356/run.log` if the live run is
  clean. Show the logged failure and the next line with the tactic switch.
- Planner rationale. Show the switch reason in the log.
- A confirmation step. Show a finding followed by a replay attack with
  `confirmation_of` set.

## 9:00 to 11:00. Report walkthrough

Open the newest file in `reports/`. Use
`reports/20261126-090434/report.md` as the prepared artifact. Show the executive
summary, five findings, exact request and response evidence, reproduction steps
and remediation. Show that there are ten attacks and thirteen evidence items.

## 11:00 to 12:00. Evaluation and production

Open `eval/results/evaluation.json`. Show the table below.

| Target | ASR | TP | FP | FN |
| --- | --- | --- | --- | --- |
| LegacyBot | 0.5 | 5 | 0 | 0 |
| SecureBot | 0.0 | 0 | 0 | 0 |

Open `docs/PRODUCTION.md`. End with the honest answer. Not production-grade.
Needs isolation, independent judges, durable jobs, strict authorization and
human review.

## After the GPU run

Once the tunnel URL is pasted back, set `RT_MODEL_BASE_URL` and rerun with
`--backend remote`. Show `eval/results/model_eval.json` for base versus tuned.
Then the model claim is real, not planned.

## What to record

One take. 10 to 15 minutes. Include the console, the report and the evaluation
JSON. Keep the terminal font large enough to read.
