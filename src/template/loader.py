import copy
from pathlib import Path

import yaml

from .parser import TemplateError, parse_template
from .registry import TemplateRegistry
from .template import Template


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _merge_overrides(merged: dict, overrides: dict) -> None:
    page_number = overrides["page"]
    page = next((p for p in merged["pages"] if p["page"] == page_number), None)

    if page is None:
        raise TemplateError(f"Override references page {page_number}, which doesn't exist in base.")

    for section_override in overrides.get("sections", []):
        section_id = section_override["id"]
        section = next((s for s in page["sections"] if s["id"] == section_id), None)

        if section is None:
            raise TemplateError(
                f"Override references section '{section_id}', which doesn't exist on page {page_number}."
            )

        section["fields"].extend(section_override.get("add_fields", []))


def _resolve_variant(base_data: dict, variant_data: dict) -> dict:
    merged = copy.deepcopy(base_data)

    merged["id"] = variant_data["id"]
    merged["name"] = variant_data.get("name", merged.get("name", merged["id"]))
    merged["metadata"] = {**merged.get("metadata", {}), **variant_data.get("metadata", {})}

    if "registration" in variant_data:
        merged["registration"] = variant_data["registration"]

    overrides = variant_data.get("overrides")
    if overrides:
        _merge_overrides(merged, overrides)

    return merged


def load_base(family_dir: Path, family: str) -> Template:
    base_data = _load_yaml(family_dir / "base.yaml")
    return parse_template(base_data, family)


def load_variant(family_dir: Path, variant_filename: str, family: str) -> Template:
    base_data = _load_yaml(family_dir / "base.yaml")
    variant_data = _load_yaml(family_dir / "variants" / variant_filename)
    merged = _resolve_variant(base_data, variant_data)
    return parse_template(merged, family)


def load_family(templates_dir: Path, family: str) -> TemplateRegistry:
    family_dir = templates_dir / family
    registry = TemplateRegistry()

    for variant_path in sorted((family_dir / "variants").glob("*.yaml")):
        registry.register(load_variant(family_dir, variant_path.name, family))

    return registry
