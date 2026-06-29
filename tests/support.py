"""Test helpers shared across modules (kept out of conftest for clean imports)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

API_BASE = "https://api.poiskkino.dev"
FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))
