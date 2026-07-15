"""Core configuration hygiene detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfigHygiene:
    has_env_sample: bool


def detect_config_hygiene(root: Path) -> ConfigHygiene:
    """Detect configuration hygiene in *root*. Read-only."""
    has_env = (root / ".env.sample").exists() or (root / ".env.example").exists()
    return ConfigHygiene(has_env_sample=has_env)
