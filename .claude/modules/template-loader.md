# Module: template loader (loader + parser + registry)

First real module of Phase 1. Files: `src/template/loader.py`, `parser.py`, `registry.py` (all currently empty).

## Goal
Turn template YAML into validated, in-memory `Template` objects. Resolve `base + variant` inheritance into a
single flat template, and index loaded templates so the pipeline can look one up. It does **not** do any
extraction, registration, or coordinate capture.

## Inputs
- `templates/<family>/base.yaml` and `templates/<family>/variants/*.yaml`.
  - `base.yaml`: `id`, `name`, `inherits: null`, `metadata`, `pages → sections → fields` (field id lists).
  - variant: `id`, `inherits: base.yaml`, `metadata.variant`, `overrides:` with `add_fields:` (and likely
    `remove_fields` / field-level overrides as the schema grows).
- The `src/template/` config dataclasses define the **target shape** — read them first:
  `Template, PageConfig, SectionConfig, FieldConfig, ROIConfig, OCRConfig, ValidationConfig, ExportConfig,
  RegistrationConfig, PreprocessingConfig, TemplateMetadata` + `enums.py`.

## Outputs
- A fully-resolved `Template` instance (inheritance merged, variant overrides applied).
- A `TemplateRegistry` that holds loaded templates and looks them up by id / family.
- Contract for downstream: `registration/` asks the registry which `Template` a scanned page matches; everything
  else reads fields/ROIs off the resolved `Template`.

## Dependencies
- PyYAML (add to `requirements.txt` — confirm with owner before editing it).
- Nothing else; this is the root of the dependency graph.

## Design decisions (this module)
- **Field metadata is inline, not schema-joined.** Resolved — see decisions.md D9. Every field in
  `base.yaml`/`variants/*.yaml` carries its full `FieldConfig` shape (`id, label, datatype, widget, roi, ocr,
  validation, export`) directly. No `templates/schema/*.yaml` join step; those placeholder files are removed.
  The loader is a straight YAML → dataclass deserializer plus base+variant inheritance merge.
- Inheritance merge semantics: variant's `overrides.sections[].add_fields` appends full field dicts to the
  matching base section (matched by `id`); `repeatable` / `max_items` carried on `SectionConfig` (see
  `nominee`, `max_items: 2`).
- Validation on load: fail fast on unknown field ids referenced by overrides, **duplicate field ids
  template-wide** (not just per-section — D9), missing required keys.

## Open questions
- ROI coords are absent at this stage and get filled by the annotator (#2). Loader tolerates a missing
  `roi:` key in YAML by defaulting to `ROIConfig(None, None, None, None)` (template valid but not yet
  annotated) and should expose whether a template is "annotated / ready".

## Tests — done
- `tests/test_template_loader.py` (6 tests, all passing): base loads with 90 unique fields across 2 pages;
  `premier_lfq` adds `optional_atpd_sum_assured` to `payment_details`; `secure_lfq` adds `rider_sum_assured`;
  `load_family` registers both variants; `nominee` section resolves as repeatable with `max_items=2`;
  fail-fast on a duplicate field id and on an override targeting a nonexistent section.
- Smoke-tested: `load_family(Path("templates"), "axis_max")` loads both variants, printed the resolved
  section/field-count tree for `premier_lfq` — `payment_details` correctly shows 12 fields (11 base + 1
  variant addition).
