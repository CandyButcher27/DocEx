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
- **Where field metadata (datatype/roi/ocr/validation) comes from.** `base.yaml` currently lists field *ids*
  only — `FieldConfig` needs datatype, ROI, OCR, validation, export per field. Decide: do these live in
  `templates/schema/*.yaml` (field_types.yaml, validation.yaml — currently empty) and get joined by id, or
  inline in the template YAML? Resolve and record here. This is the main open design question.
- Inheritance merge semantics: how `add_fields` / overrides combine with the base section list; section
  matching by `id`; handling `repeatable` / `max_items` sections (see `nominee`).
- Validation on load: fail fast on unknown field ids, duplicate ids, missing referenced schema entries.

## Open questions
- Schema-join vs inline field metadata (above) — **blocks** ROIConfig/OCRConfig population, so settle early.
- ROI coords are absent at this stage and get filled by the annotator (#2). Loader should tolerate
  `ROIConfig` with `None` coords (template valid but not yet annotated) and expose whether a template is
  "annotated / ready".

## Tests
- `tests/test_template_loader.py`: load `axis_max` base, assert section/field counts; load `premier_lfq`
  and assert `optional_atpd_sum_assured` was added to `payment_details`; assert `secure_lfq` resolves; assert
  fail-fast on a malformed template.
- Smoke: load all `templates/axis_max/*` and print the resolved field tree for one variant.
