#!/usr/bin/env python3
"""Cross-platform launcher for running VK and Telegram bots together."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.entrypoints.all import run


if __name__ == "__main__":
    raise SystemExit(run())
