import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_STORE = ROOT / "template_store"
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "output" / "_work"

RENDER_DPI = 200
GHOSTSCRIPT_BIN = "gswin64c"

ANCHOR_MATCH_THRESHOLD = 0.72
CLASSIFY_TEXT_THRESHOLD = 0.60
PHASH_MAX_DISTANCE = 12

ACCEPT_CONFIDENCE = 0.80
REVIEW_CONFIDENCE = 0.50

for _d in (TEMPLATE_STORE, OUTPUT_DIR, WORK_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def vlm_settings() -> dict:
    from .env import load_env
    load_env()
    provider = os.environ.get("VLM_PROVIDER", "").lower()
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    ollama_key = os.environ.get("OLLAMA_API_KEY", "")
    if not provider:
        provider = "gemini" if gemini_key else ("ollama" if ollama_key else "fake")
    return {
        "provider": provider,
        "gemini_key": gemini_key,
        "gemini_model": os.environ.get("VLM_MODEL") or "gemini-2.5-flash",
        "ollama_key": ollama_key,
        "ollama_base": os.environ.get("OLLAMA_BASE_URL", "https://ollama.com/v1"),
        "ollama_model": os.environ.get("OLLAMA_MODEL", "gemma3:27b"),
    }
