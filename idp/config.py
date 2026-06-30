from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_STORE = ROOT / "template_store"
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "output" / "_work"

RENDER_DPI = 200
GHOSTSCRIPT_BIN = "gswin64c"

ANCHOR_MATCH_THRESHOLD = 0.72
CLASSIFY_TEXT_THRESHOLD = 0.45
PHASH_MAX_DISTANCE = 12

ACCEPT_CONFIDENCE = 0.80
REVIEW_CONFIDENCE = 0.50

for _d in (TEMPLATE_STORE, OUTPUT_DIR, WORK_DIR):
    _d.mkdir(parents=True, exist_ok=True)
