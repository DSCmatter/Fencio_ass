"""Render Markdown and HTML reports from persisted assessment state."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models import AssessmentState, Severity

TEMPLATES = Path(__file__).parent / "templates"


def generate_report(state: AssessmentState, output_dir: Path, model_label: str) -> tuple[Path, Path]:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        keep_trailing_newline=True,
    )
    evidence_by_finding: dict[str, list] = defaultdict(list)
    for item in state.evidence:
        evidence_by_finding[item.finding_id].append(item)
    counts = {severity.value: 0 for severity in Severity}
    for finding in state.findings:
        counts[finding.severity.value] += 1
    context = {
        "state": state,
        "model_label": model_label,
        "counts": counts,
        "categories_tested": len({record.category for record in state.tested}),
        "evidence_by_finding": dict(evidence_by_finding),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown = env.get_template("report.md.j2").render(**context)
    html = env.get_template("report.html.j2").render(**context)
    md_path = output_dir / "report.md"
    html_path = output_dir / "report.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return md_path, html_path
