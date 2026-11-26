"""Configuration loading with environment-variable expansion."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name, default = match.group(1), match.group(2)
            return os.environ.get(name, default if default is not None else "")
        return _ENV_REF.sub(replace, value)
    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env(item) for item in value]
    return value


class ModelConfig(BaseModel):
    backend: str = "auto"
    base_url: str = ""
    api_key_env: str = "RT_MODEL_API_KEY"
    model_name: str = ""
    timeout_s: float = 60.0
    max_retries: int = 3


class TargetConfig(BaseModel):
    base_url: str = "http://127.0.0.1:8001"
    name: str = "Vulnerable target"


class BudgetConfig(BaseModel):
    max_recon_questions: int = 6
    max_attacks_per_category: int = 8
    max_total_attacks: int = 60
    max_followups_per_finding: int = 2
    switch_after_failures: int = 2


class RunConfig(BaseModel):
    output_dir: str = "reports"
    state_db: str = "reports/state/assessment.db"
    seed: int = 1337
    log_level: str = "INFO"


class Config(BaseModel):
    model: ModelConfig
    target: TargetConfig
    budgets: BudgetConfig
    run: RunConfig


def load_config(path: str | Path = "configs/agent.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config.model_validate(expand_env(raw))
