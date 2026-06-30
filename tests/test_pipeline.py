import json
from pathlib import Path

from src.configs.settings import Settings
from src.models.document import ExtractionRoute
from src.pipeline.orchestrator import extract_document
from src.template.enums import ExportFormat
from synthetic import make_page


def _settings(templates_dir: Path, output_dir: Path) -> Settings:
    return Settings(
        ocr_engine="stub",
        vlm_provider="fake",
        anthropic_api_key="",
        openai_api_key="",
        vlm_model="",
        registration_match_threshold=0.18,
        registration_min_inliers=12,
        poppler_path="",
        templates_dir=templates_dir,
        output_dir=output_dir,
    )


def test_unknown_doc_routes_to_vlm_and_generates_template(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    settings = _settings(templates_dir, tmp_path)
    pages = [make_page(seed=20), make_page(seed=21)]

    result = extract_document(
        "demo.pdf",
        settings=settings,
        export_format=ExportFormat.JSON,
        output_path=tmp_path / "out",
        page_images=pages,
    )

    assert result.route == ExtractionRoute.VLM_FALLBACK
    assert result.template_id == "auto_generated_auto"
    assert (templates_dir / "auto_generated" / "base.yaml").exists()
    assert result.export_path.exists()

    data = json.loads(result.export_path.read_text(encoding="utf-8"))
    assert len(data["fields"]) == 4
    assert data["fields"][0]["value"] == "SAMPLE"


def test_known_doc_takes_template_path_on_second_run(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    settings = _settings(templates_dir, tmp_path)
    pages = [make_page(seed=30), make_page(seed=31)]

    first = extract_document("demo.pdf", settings=settings, page_images=pages)
    assert first.route == ExtractionRoute.VLM_FALLBACK

    second = extract_document("demo.pdf", settings=settings, page_images=pages)
    assert second.route == ExtractionRoute.TEMPLATE_MATCH
    assert second.template_id == "auto_generated_auto"
    assert second.match_score >= 0.18
    assert len(second.document.all_fields()) == 4
