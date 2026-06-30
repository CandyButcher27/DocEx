# Architecture (canonical reference)

This is the source of truth for how the system fits together. If code and this doc disagree, one of them
is wrong — fix the drift, don't ignore it.

## Pipeline flow

```
PDF (scanned_docs/)
   │  PDF loader            → page images
   ▼
Preprocessing              → cleaned page images (deskew / denoise / binarize)
   │
   ▼
Template registration      → which known Template does this doc match? + page alignment to the reference
   │
   ▼  (match)                                         (no match → VLM-fallback path, Phase 2)
ROI extraction             → crop each field's region from the aligned page
   │
   ▼
OCR                        → OCRResult per crop
   │
   ▼
Validation + confidence    → ValidationResult per field, scored
   │
   ▼
Export                     → JSON / CSV / Excel
```

## The two paths

**1. Template-match (deterministic) — Phase 1.**
A scanned doc is matched to a registered `Template`. The template carries, per field, a normalized region
of interest (ROI). We align the scanned page to the template's reference, crop each ROI, OCR it, validate,
export. Cheap and repeatable.

**2. VLM-fallback (unknown doc) — Phase 2.**
No template matches. A VLM infers the document's field structure. OCR still does the text extraction. The
result is exported, **and** the inferred structure is written out as a new template (with ROIs) so the next
similar document takes path 1. The VLM provider is deliberately undecided — keep it behind an interface.

## Data model — two distinct layers

Keep these straight; they are easy to confuse.

- **`src/template/` — configuration (static, loaded from YAML).** Immutable description of *what* a document
  type contains and *how* to extract it. `Template → pages → sections → FieldConfig`, where each `FieldConfig`
  holds `ROIConfig`, `OCRConfig`, `ValidationConfig`, `ExportConfig`. Built as `frozen, slots` dataclasses.
- **`src/models/` — runtime objects (per-document, mutable where needed).** What actually happens to one real
  document as it flows through the pipeline: `Document → Page → Field`, where a `Field` bundles its
  `FieldConfig` (from the template) with the `OCRResult` and `ValidationResult` produced at runtime.

So: **config describes the template; models describe one document's pass through the pipeline.**

## Module responsibilities + I/O contracts

Each pipeline stage is one module under `src/`. The contract is the type it consumes and the type it produces —
honor these so modules stay swappable and independently testable.

| Module | Responsibility | Input | Output |
|---|---|---|---|
| `template/` (loader+parser+registry) | YAML → `Template` objects; resolve base+variant inheritance; index templates | YAML files | `Template`, `TemplateRegistry` |
| `tools/roi_annotator.py` | GUI to capture normalized field coordinates onto YAML | reference image + field list | ROIs written into template YAML |
| PDF loader + `preprocessing/` | PDF → page images; deskew / denoise / binarize | PDF path | cleaned page images |
| `registration/` | match doc to a template + align page to its reference image | page image, registry | matched `Template`, aligned page |
| `roi/` | crop each field's region from the aligned page | aligned page, `ROIConfig` | per-field image crops |
| `ocr/` | run OCR engine (pluggable) on a crop | crop, `OCRConfig` | `OCRResult` |
| `validation/` + `confidence/` | normalize, validate, score a field's OCR output | `OCRResult`, `ValidationConfig` | `ValidationResult` |
| `exporters/` | serialize results | `list[Field]`, `ExportConfig` | JSON / CSV / Excel |
| `pipeline/` | orchestrate all stages over one document | PDF path, registry | exported file |
| `configs/` | system configuration | — | settings |
| `utils/` | shared helpers | — | — |

## Cross-cutting notes

- **docx → image.** `proper_docs/` references are `.docx`; registration needs reference *images*. A render
  step (docx → image, or maintain a rendered reference per template) is required. `RegistrationConfig` already
  carries `reference_images: dict[int, str]`.
- **PDF page handling.** `scanned_docs/` are multi-page PDFs. The loader must page-split; templates are
  defined per page (`pages: list[PageConfig]`).
- **The ROI-coordinate gap.** Templates currently list *what* fields exist but **not where** — `base.yaml`
  has no coordinates and `ROIConfig` fields are all `None`. Nothing downstream of registration can run until
  ROIs are populated. The **GUI annotator** (`tools/roi_annotator.py`) is the chosen bridge: click each field's
  box on the reference image, write normalized `[0,1]` coords back into the template YAML. This is why the
  annotator is module #2 in the roadmap, right after the loader.
- **Normalized coordinates.** All ROIs are stored as floats in `[0,1]` (see `ROI.to_pixels`), so a template is
  resolution-independent and survives rescaling between the reference and a scanned page.
