#!/usr/bin/env python3
"""Cross-platform launcher for VK bot (Windows/Ubuntu)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.entrypoints.vk import run


if __name__ == "__main__":
    raise SystemExit(run())
