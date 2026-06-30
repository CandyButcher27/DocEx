from __future__ import annotations

import os
from pathlib import Path

_loaded = False


def load_env(path: str | Path | None = None) -> None:
    global _loaded
    if _loaded:
        return
    from .config import ROOT
    p = Path(path) if path else ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
    _loaded = True
