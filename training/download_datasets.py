"""Download the licence-verified public datasets into data/raw/.

Original files are copied byte-for-byte into ``data/raw/<slug>/orig/`` and the
same rows are additionally written as JSONL so the preparation step can read a
single, uniform format. No cleaning, filtering or rewriting happens here.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datasets import load_dataset
from huggingface_hub import hf_hub_download

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"


@dataclass(frozen=True)
class SourceSpec:
    slug: str
    repo_id: str
    licence: str
    licence_url: str
    card_url: str
    licence_note: str
    files: tuple[tuple[str, str], ...]  # (huggingface filename, JSONL split name)


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        slug="deepset_prompt-injections",
        repo_id="deepset/prompt-injections",
        licence="apache-2.0",
        licence_url="https://huggingface.co/datasets/deepset/prompt-injections",
        card_url="https://huggingface.co/datasets/deepset/prompt-injections/raw/main/README.md",
        licence_note=(
            "The dataset card's top-level license field and the HF tag say apache-2.0. "
            "The stale nested dataset_info.license field still says cc-by-4.0; both are "
            "permissive. No LICENSE file is present in the repo (PR #4 adding one is open)."
        ),
        files=(
            ("data/train-00000-of-00001-9564e8b05b4757ab.parquet", "train"),
            ("data/test-00000-of-00001-701d16158af87368.parquet", "test"),
        ),
    ),
    SourceSpec(
        slug="JailbreakBench_JBB-Behaviors",
        repo_id="JailbreakBench/JBB-Behaviors",
        licence="mit",
        licence_url="https://raw.githubusercontent.com/JailbreakBench/jailbreakbench/main/LICENSE",
        card_url="https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/raw/main/README.md",
        licence_note="Dataset card declares MIT; linked repository LICENSE file is MIT. gated=false.",
        files=(
            ("data/harmful-behaviors.csv", "harmful"),
            ("data/benign-behaviors.csv", "benign"),
            ("data/judge-comparison.csv", "judge_comparison"),
        ),
    ),
    SourceSpec(
        slug="jackhhao_jailbreak-classification",
        repo_id="jackhhao/jailbreak-classification",
        licence="apache-2.0",
        licence_url="https://huggingface.co/datasets/jackhhao/jailbreak-classification",
        card_url="https://huggingface.co/datasets/jackhhao/jailbreak-classification/raw/main/README.md",
        licence_note="Dataset card front matter and HF tag declare Apache-2.0. gated=false.",
        files=(
            ("balanced/jailbreak_dataset_train_balanced.csv", "train_balanced"),
            ("balanced/jailbreak_dataset_test_balanced.csv", "test_balanced"),
        ),
    ),
    SourceSpec(
        slug="S-Labs_prompt-injection-dataset",
        repo_id="S-Labs/prompt-injection-dataset",
        licence="mit",
        licence_url="https://huggingface.co/datasets/S-Labs/prompt-injection-dataset/raw/main/README.md",
        card_url="https://huggingface.co/datasets/S-Labs/prompt-injection-dataset/raw/main/README.md",
        licence_note="Dataset card front matter, HF tag and the 'License' section declare MIT. gated=false.",
        files=(
            ("data/train.csv", "train"),
            ("data/validation.csv", "validation"),
            ("data/test.csv", "test"),
        ),
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_one(spec: SourceSpec, filename: str, split_name: str) -> dict[str, Any]:
    cached = Path(
        hf_hub_download(repo_id=spec.repo_id, filename=filename, repo_type="dataset")
    )
    destination_dir = RAW_ROOT / spec.slug / "orig"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / Path(filename).name
    shutil.copy2(cached, destination)

    loader = "parquet" if filename.endswith(".parquet") else "csv"
    rows = list(load_dataset(loader, data_files=str(destination), split="train"))
    jsonl_path = RAW_ROOT / spec.slug / f"{split_name}.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    return {
        "file": filename,
        "split": split_name,
        "resolve_url": (
            f"https://huggingface.co/datasets/{spec.repo_id}/resolve/main/{filename}"
        ),
        "sha256": _sha256(destination),
        "bytes": destination.stat().st_size,
        "rows": len(rows),
        "jsonl": str(jsonl_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }


def download_all() -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "sources": [],
        "failures": [],
    }
    for spec in SOURCES:
        entry: dict[str, Any] = {
            "repo_id": spec.repo_id,
            "slug": spec.slug,
            "license": spec.licence,
            "license_url": spec.licence_url,
            "card_url": spec.card_url,
            "license_note": spec.licence_note,
            "files": [],
        }
        for filename, split_name in spec.files:
            try:
                entry["files"].append(_download_one(spec, filename, split_name))
            except Exception as exc:  # record the failure rather than hiding it
                manifest["failures"].append(
                    {
                        "repo_id": spec.repo_id,
                        "file": filename,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        manifest["sources"].append(entry)
    manifest_path = RAW_ROOT / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    manifest = download_all()
    for source in manifest["sources"]:
        total = sum(file_info["rows"] for file_info in source["files"])
        print(f"{source['repo_id']}: {total} rows ({source['license']})")
    for failure in manifest["failures"]:
        print(f"FAILED {failure['repo_id']}/{failure['file']}: {failure['error']}")
    print(f"Manifest: {RAW_ROOT / 'manifest.json'}")


if __name__ == "__main__":
    main()
