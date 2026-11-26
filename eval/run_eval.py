"""Evaluation harness. Every number written here comes from a real CLI run."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml

from redteam.models import AttackCategory, Verdict
from redteam.state import StateStore

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the red team agent.")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--config", default="configs/agent.yaml")
    parser.add_argument("--legacy-url", default="http://127.0.0.1:7003/v1/chat/completions")
    parser.add_argument("--secure-url", default="http://127.0.0.1:7001/v1/chat/completions")
    parser.add_argument("--ground-truth", default="eval/ground_truth.yaml")
    parser.add_argument("--out", default="eval/results/evaluation.json")
    return parser.parse_args(argv)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_one(url: str, label: str, index: int, config: str) -> dict[str, Any]:
    """Run one fresh assessment. Keep its raw stdout as evidence."""
    state_db = RESULTS / f"{label}-run-{index}.db"
    log_path = RESULTS / f"{label}-run-{index}.log"
    cmd = [
        sys.executable, "-m", "redteam.cli", "run",
        "--config", config,
        "--target", url,
        "--state-db", str(state_db),
        "--backend", "deterministic",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    log_path.write_text(proc.stdout + "\n[stderr]\n" + proc.stderr, encoding="utf-8")
    return {
        "index": index,
        "state_db": str(state_db.relative_to(ROOT)),
        "log": str(log_path.relative_to(ROOT)),
        "returncode": proc.returncode,
        "command": " ".join(cmd),
    }


def summarize(manifest: list[dict[str, Any]], expected: list[str]) -> dict[str, Any]:
    attacks: list[Any] = []
    for entry in manifest:
        if entry["returncode"] != 0:
            continue
        attacks.extend(StateStore(ROOT / entry["state_db"]).load_attacks())

    confirmed = [a for a in attacks if a.verdict == Verdict.CONFIRMED]
    found = sorted({a.category.value for a in confirmed})
    expected_set = set(expected)

    first_success: dict[str, int] = {}
    for category in {a.category.value for a in attacks}:
        matches = [i for i, a in enumerate(attacks, start=1)
                   if a.category.value == category and a.verdict == Verdict.CONFIRMED]
        if matches:
            first_success[category] = matches[0]

    true_positives = sorted(expected_set & set(found))
    false_negatives = sorted(expected_set - set(found))
    false_positives = sorted(set(found) - expected_set)
    means = list(first_success.values())

    return {
        "runs_requested": len(manifest),
        "runs_completed": sum(1 for m in manifest if m["returncode"] == 0),
        "total_attacks": len(attacks),
        "successful_attacks": len(confirmed),
        "attack_success_rate": round(len(confirmed) / len(attacks), 4) if attacks else None,
        "expected_findings": sorted(expected_set),
        "confirmed_categories": found,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "detection_rate": round(len(true_positives) / len(expected_set), 4) if expected_set else None,
        "attacks_to_first_success_by_category": first_success,
        "mean_attacks_to_first_success": round(statistics.mean(means), 4) if means else None,
        "per_run": manifest,
    }


def main(args: argparse.Namespace | Sequence[str] | None = None) -> int:
    if args is None or isinstance(args, (list, tuple)):
        args = _parse(args)
    elif not hasattr(args, "runs"):
        args = _parse(None)

    RESULTS.mkdir(parents=True, exist_ok=True)
    ground_truth = getattr(args, "ground_truth", "eval/ground_truth.yaml")
    out_path_arg = getattr(args, "out", "eval/results/evaluation.json")
    config = getattr(args, "config", "configs/agent.yaml")
    runs = getattr(args, "runs", 5)
    truth = yaml.safe_load((ROOT / ground_truth).read_text(encoding="utf-8"))["targets"]

    output: dict[str, Any] = {
        "generated_at": _utcnow(),
        "backend": "deterministic",
        "model_label": "deterministic:rule-v1",
        "note": "Rule-based offline backend. No GPU model loaded. Numbers are from real CLI runs.",
        "limits": [
            "Small sample size. Five runs per target.",
            "Rule-based attacker, not the fine-tuned model.",
            "LegacyBot is an intentionally vulnerable simulator, not a production agent.",
            "Indirect-injection success is instruction override, not fetched-page execution.",
        ],
        "targets": {},
    }

    for label in ("legacy", "secure"):
        spec = truth[label]
        manifest = [
            run_one(spec["url"], label, i, config)
            for i in range(1, runs + 1)
        ]
        metrics = summarize(manifest, spec.get("expected_findings", []))
        metrics["name"] = spec["name"]
        metrics["url"] = spec["url"]
        metrics["note"] = spec.get("note", "")
        output["targets"][label] = metrics
        print(
            f"[eval] {spec['name']}: ASR={metrics['attack_success_rate']} "
            f"TP={len(metrics['true_positives'])} FP={len(metrics['false_positives'])} "
            f"FN={len(metrics['false_negatives'])}"
        )

    out_path = ROOT / out_path_arg
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[eval] results written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
