import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Settings:
    ocr_engine: str
    vlm_provider: str
    anthropic_api_key: str
    openai_api_key: str
    vlm_model: str
    registration_match_threshold: float
    registration_min_inliers: int
    poppler_path: str
    templates_dir: Path
    output_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(REPO_ROOT / ".env")

    return Settings(
        ocr_engine=os.getenv("OCR_ENGINE", "stub").strip().lower(),
        vlm_provider=os.getenv("VLM_PROVIDER", "fake").strip().lower(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        vlm_model=os.getenv("VLM_MODEL", "").strip(),
        registration_match_threshold=float(os.getenv("REGISTRATION_MATCH_THRESHOLD", "0.18")),
        registration_min_inliers=int(os.getenv("REGISTRATION_MIN_INLIERS", "12")),
        poppler_path=os.getenv("POPPLER_PATH", "").strip(),
        templates_dir=Path(os.getenv("TEMPLATES_DIR", str(REPO_ROOT / "templates"))),
        output_dir=Path(os.getenv("OUTPUT_DIR", str(REPO_ROOT / "output"))),
    )
