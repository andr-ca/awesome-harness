"""Structured merge — merge JSON/YAML key paths without overwriting unrelated
content.
"""

from __future__ import annotations

import json
from typing import Any


def merge_json_keys(
    existing_json: str,
    updates: dict[str, Any],
) -> str:
    """Merge *updates* into *existing_json*, preserving unrelated keys.

    Only the keys in *updates* are affected.
    """
    try:
        data: dict[str, Any] = (
            json.loads(existing_json) if existing_json.strip() else {}
        )
    except json.JSONDecodeError:
        data = {}

    data.update(updates)
    return json.dumps(data, sort_keys=True, indent=2)
