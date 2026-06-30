# DocEx — Document Extraction Pipeline

A template-driven pipeline for extracting structured fields from scanned documents.

Scanned documents come in as PDFs. Each is matched against a library of known **templates**. On a match,
the document is aligned, each field's region is cropped, OCR'd, validated, and exported to JSON/CSV/Excel.
When no template matches, a vision model derives the document's structure on the fly — and that structure is
saved as a new template so the next similar document takes the cheap, deterministic path.

> **Note on data:** real scanned documents and the company reference forms (`.docx`) used to build templates
> are intentionally **not** part of this repository. The pipeline, data models, and template definitions are.

## Why two paths

| | Template-match path | VLM-fallback path |
|---|---|---|
| When | Document matches a known template | No template matches |
| How | Align → crop ROIs → OCR → validate → export | VLM infers structure → OCR → export |
| Cost | Cheap, deterministic, repeatable | Higher (model tokens), runs once per new layout |
| Side effect | — | Auto-saves a reusable template |

The design goal is that the expensive VLM path runs **at most once per document layout** — every subsequent
document of that layout falls through to the deterministic path.

## Pipeline

```
PDF → Preprocessing → Registration → ROI crop → OCR → Validation/Confidence → Export
                          │
                          └── (no match) → VLM derives structure → … → save new template
```

## Repository layout

```
src/
  models/        Runtime objects for one document's pass (Document, Page, Field, ROI, OCRResult, ValidationResult)
  template/      Template config object model (loaded from YAML) + loader/parser/registry
  preprocessing/ Image cleanup (deskew, denoise, binarize)
  registration/  Match a page to a template and align it to the reference
  roi/           Crop each field's region
  ocr/           OCR engine adapters (pluggable)
  validation/    Field validators
  confidence/    Confidence scoring
  exporters/     JSON / CSV / Excel output
  pipeline/      Orchestration
templates/       Document templates as YAML (base + variant inheritance) and shared schema
tools/           ROI annotator (GUI to capture field coordinates onto templates)
tests/           Per-module tests (pytest)
.claude/         Project context for AI-assisted, module-by-module development (see below)
```

## Data model

Two layers, kept deliberately separate:

- **`src/template/` — configuration.** Immutable description of a document type loaded from YAML:
  `Template → Page → Section → FieldConfig`, where each field carries its ROI, OCR, validation, and export config.
- **`src/models/` — runtime.** What happens to one real document as it flows through the pipeline:
  `Document → Page → Field`, where a `Field` bundles its config with the produced `OCRResult` and `ValidationResult`.

Templates use **inheritance**: a `base.yaml` plus `variants/*.yaml` that declare `inherits:` and only their
overrides — so variants of a form share one schema instead of duplicating it.

ROI coordinates are stored **normalized to `[0, 1]`** (resolution-independent), so one template works across
scan resolutions.

## Status

Built module-by-module. Current phase: **deterministic template-match track, end-to-end.**

- ✅ Runtime data models and template config object model
- ✅ Axis Max LFQ template (base + Premier/Secure variants)
- 🚧 Template loader (YAML → `Template` objects) — next
- ⬜ Annotator, preprocessing, registration, ROI, OCR, validation, export, pipeline orchestration
- ⬜ VLM-fallback track (after the deterministic path works end-to-end)

See [`.claude/status.md`](.claude/status.md) for the live tracker and [`.claude/roadmap.md`](.claude/roadmap.md)
for the build order.

## Development

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Linux/WSL
pip install -r requirements.txt
pytest
```

This project is developed incrementally, one module per session. The [`.claude/`](.claude/) directory holds the
architecture, locked decisions, conventions, and per-module specs so any contributor (human or AI) can pick up
exactly where the last left off. Start at [`.claude/CLAUDE.md`](.claude/CLAUDE.md).
