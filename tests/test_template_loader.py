import unittest
from pathlib import Path

import pytest

from src.template.loader import load_base, load_family, load_variant
from src.template.parser import TemplateError, parse_template

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
FAMILY_DIR = TEMPLATES_DIR / "axis_max"


def _section(template, page_number, section_id):
    page = next(p for p in template.pages if p.number == page_number)
    return next(s for s in page.sections if s.id == section_id)


class TestTemplateLoader(unittest.TestCase):

    def test_load_base(self):
        template = load_base(FAMILY_DIR, "axis_max")

        self.assertEqual(template.metadata.template_id, "axis_max_lfq_base")
        self.assertEqual(template.metadata.variant, "Base")
        self.assertEqual(len(template.pages), 2)

        field_ids = [
            field.id
            for page in template.pages
            for section in page.sections
            for field in section.fields
        ]
        self.assertEqual(len(field_ids), 90)
        self.assertEqual(len(set(field_ids)), 90)

    def test_load_premier_variant_adds_field(self):
        template = load_variant(FAMILY_DIR, "premier_lfq.yaml", "axis_max")

        self.assertEqual(template.metadata.template_id, "axis_max_lfq_premier")
        self.assertEqual(template.metadata.variant, "Premier")

        payment_details = _section(template, 1, "payment_details")
        field_ids = [f.id for f in payment_details.fields]
        self.assertIn("optional_atpd_sum_assured", field_ids)

    def test_load_secure_variant_resolves(self):
        template = load_variant(FAMILY_DIR, "secure_lfq.yaml", "axis_max")

        self.assertEqual(template.metadata.template_id, "axis_max_lfq_secure")
        self.assertEqual(template.metadata.variant, "Secure")

        payment_details = _section(template, 1, "payment_details")
        field_ids = [f.id for f in payment_details.fields]
        self.assertIn("rider_sum_assured", field_ids)

    def test_load_family_registers_both_variants(self):
        registry = load_family(TEMPLATES_DIR, "axis_max")

        self.assertEqual(len(registry), 2)
        self.assertEqual(
            {t.metadata.template_id for t in registry.all()},
            {"axis_max_lfq_premier", "axis_max_lfq_secure"},
        )

    def test_nominee_section_is_repeatable(self):
        template = load_base(FAMILY_DIR, "axis_max")
        nominee = _section(template, 1, "nominee")

        self.assertTrue(nominee.repeatable)
        self.assertEqual(nominee.max_items, 2)

    def test_fail_fast_on_duplicate_field_id(self):
        malformed = {
            "id": "malformed_template",
            "metadata": {
                "variant": "Base",
                "version": "1.0",
                "issuer": "Test Issuer",
                "document_type": "Test Document",
            },
            "registration": {"method": "orb", "reference_images": {}},
            "preprocessing": {
                "deskew": True,
                "perspective_correction": True,
                "adaptive_threshold": True,
                "denoise": True,
                "contrast_enhancement": True,
            },
            "pages": [
                {
                    "page": 1,
                    "sections": [
                        {
                            "id": "section_a",
                            "fields": [
                                {
                                    "id": "dup_field",
                                    "label": "Dup",
                                    "datatype": "text",
                                    "widget": "textbox",
                                    "ocr": {"engine": "paddle"},
                                    "validation": {"validator": "text"},
                                }
                            ],
                        },
                        {
                            "id": "section_b",
                            "fields": [
                                {
                                    "id": "dup_field",
                                    "label": "Dup",
                                    "datatype": "text",
                                    "widget": "textbox",
                                    "ocr": {"engine": "paddle"},
                                    "validation": {"validator": "text"},
                                }
                            ],
                        },
                    ],
                }
            ],
        }

        with pytest.raises(TemplateError):
            parse_template(malformed, "test_family")

    def test_fail_fast_on_override_to_unknown_section(self):
        from src.template.loader import _resolve_variant

        with self.assertRaises(TemplateError):
            base_data = {
                "id": "base",
                "name": "Base",
                "metadata": {"variant": "Base", "version": "1.0", "issuer": "X", "document_type": "Y"},
                "pages": [{"page": 1, "sections": [{"id": "real_section", "fields": []}]}],
            }
            variant_data = {
                "id": "variant",
                "inherits": "base.yaml",
                "metadata": {"variant": "V"},
                "overrides": {
                    "page": 1,
                    "sections": [{"id": "nonexistent_section", "add_fields": []}],
                },
            }
            _resolve_variant(base_data, variant_data)


if __name__ == "__main__":
    unittest.main()
