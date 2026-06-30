from pathlib import Path

from src.template.loader import load_all_templates
from src.vlm.fake import FakeVLMProvider
from src.vlm.prompt import extract_json, parse_derived_document
from src.vlm.template_builder import save_generated_template
from synthetic import make_page


def test_fake_derives_fields_per_page():
    provider = FakeVLMProvider()
    pages = [make_page(seed=1), make_page(seed=2)]
    derived = provider.derive_structure(pages, family_hint="demo_family")
    assert derived.family == "demo_family"
    assert len(derived.pages) == 2
    assert all(len(p.sections[0].fields) == 2 for p in derived.pages)


def test_save_generated_template_is_loadable(tmp_path):
    provider = FakeVLMProvider()
    pages = [make_page(seed=3)]
    derived = provider.derive_structure(pages, family_hint="demo_family")

    base_path = save_generated_template(derived, pages, tmp_path, ocr_engine="stub")
    assert base_path.exists()

    registry = load_all_templates(tmp_path)
    template = registry.get("demo_family_auto")
    fields = [f for pg in template.pages for s in pg.sections for f in s.fields]
    assert len(fields) == 2
    assert all(f.roi.x is not None for f in fields)


def test_extract_json_parses_fenced():
    raw = '```json\n{"family":"f","issuer":"i","document_type":"d","pages":[]}\n```'
    data = extract_json(raw)
    doc = parse_derived_document(data)
    assert doc.family == "f"
    assert doc.pages == []
