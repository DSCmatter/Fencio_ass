"""Command line entry point for the red teaming agent."""
from __future__ import annotations

import argparse
from typing import Sequence

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m redteam.cli",
        description="Autonomous AI agent red teaming system.",
    )
    parser.add_argument("--version", action="version", version=f"redteam {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="Run an assessment against a target")
    run.add_argument("--config", default="configs/agent.yaml")
    run.add_argument("--target", help="Override target base URL")
    run.add_argument("--state-db", help="Override SQLite state path")
    run.add_argument("--backend", choices=["remote", "deterministic"], help="Override model backend")
    run.add_argument("--resume", action="store_true", help="Resume from saved state")

    replay = subparsers.add_parser("replay", help="Replay attacks from saved state")
    replay.add_argument("--state-db", default="reports/state/assessment.db")

    ev = subparsers.add_parser("eval", help="Run the evaluation harness")
    ev.add_argument("--runs", type=int, default=5)
    ev.add_argument("--config", default="configs/agent.yaml")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "run":
        from .orchestrator import run_assessment
        return run_assessment(args)
    if args.command == "replay":
        from .orchestrator import replay_attacks
        return replay_attacks(args)
    if args.command == "eval":
        from eval.run_eval import main as run_eval
        return run_eval(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
