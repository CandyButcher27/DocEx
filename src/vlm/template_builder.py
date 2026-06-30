import re
from pathlib import Path

import cv2
import numpy as np
import yaml

from .schema import DerivedDocument

REPO_ROOT = Path(__file__).resolve().parents[2]


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug or "auto_generated"


def _dedupe_field_ids(document: DerivedDocument) -> dict:
    seen: set[str] = set()
    pages = []
    for page in document.pages:
        sections = []
        for section in page.sections:
            fields = []
            for f in section.fields:
                field_id = f.id
                suffix = 2
                while field_id in seen:
                    field_id = f"{f.id}_{suffix}"
                    suffix += 1
                seen.add(field_id)
                fields.append((field_id, f))
            sections.append((section.id, fields))
        pages.append((page.number, sections))
    return pages


def build_template_dict(document: DerivedDocument, template_id: str, ocr_engine: str, reference_images: dict[int, str]) -> dict:
    pages_struct = _dedupe_field_ids(document)

    yaml_pages = []
    for page_number, sections in pages_struct:
        yaml_sections = []
        for section_id, fields in sections:
            yaml_fields = []
            for field_id, f in fields:
                yaml_fields.append(
                    {
                        "id": field_id,
                        "label": f.label,
                        "datatype": f.datatype,
                        "widget": f.widget,
                        "roi": {
                            "x": round(f.x, 4),
                            "y": round(f.y, 4),
                            "width": round(f.width, 4),
                            "height": round(f.height, 4),
                        },
                        "ocr": {"engine": ocr_engine},
                        "validation": {"validator": f.validator},
                    }
                )
            yaml_sections.append({"id": section_id, "fields": yaml_fields})
        yaml_pages.append({"page": page_number, "sections": yaml_sections})

    return {
        "id": template_id,
        "name": f"{document.document_type} (auto)",
        "inherits": None,
        "metadata": {
            "issuer": document.issuer,
            "document_type": document.document_type,
            "version": "1.0-auto",
            "variant": "Auto",
        },
        "registration": {
            "method": "orb",
            "reference_images": {n: p for n, p in reference_images.items()},
        },
        "preprocessing": {
            "deskew": True,
            "perspective_correction": True,
            "adaptive_threshold": True,
            "denoise": True,
            "contrast_enhancement": True,
        },
        "pages": yaml_pages,
    }


def save_generated_template(
    document: DerivedDocument,
    page_images: list[np.ndarray],
    templates_dir: Path,
    ocr_engine: str = "stub",
) -> Path:
    family = _slug(document.family)
    template_id = f"{family}_auto"
    family_dir = templates_dir / family
    reference_dir = family_dir / "reference" / "rendered" / template_id
    reference_dir.mkdir(parents=True, exist_ok=True)

    reference_images: dict[int, str] = {}
    for i, image in enumerate(page_images, start=1):
        page_path = reference_dir / f"page_{i}.png"
        cv2.imwrite(str(page_path), image)
        try:
            rel = page_path.resolve().relative_to(REPO_ROOT)
            reference_images[i] = str(rel)
        except ValueError:
            reference_images[i] = str(page_path.resolve())

    template_dict = build_template_dict(document, template_id, ocr_engine, reference_images)

    family_dir.mkdir(parents=True, exist_ok=True)
    base_path = family_dir / "base.yaml"
    with base_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(template_dict, f, sort_keys=False, allow_unicode=True)

    return base_path
