# Decisions log

Append-only. One entry per locked decision. Newest at the bottom. If a decision is reversed, add a new entry
that supersedes the old one (and note which) — don't silently delete history.

Format: **Decision / Why / Consequences.**

---

## D1 — Dataclasses are `frozen=True, slots=True`
**Decision:** Template config objects and result objects are frozen, slotted dataclasses.
**Why:** A template, once loaded, must not mutate — extraction must be reproducible. `slots` drops the
per-instance `__dict__`, cutting memory and speeding attribute access (matters at high field/document counts).
**Consequences:** No attribute added at runtime. Open-ended/metadata-bag objects (if any later need dynamic
attributes) must opt out of `slots`.

## D2 — ROI coordinates are normalized to `[0,1]`
**Decision:** Every ROI stores `x, y, width, height` as floats in `[0,1]`, top-left origin; `to_pixels()`
converts on demand.
**Why:** Resolution independence. The reference image and a scanned page differ in size; normalized coords
survive rescaling so one template works across scan resolutions.
**Consequences:** Geometry validation lives in `ROI.__post_init__` (bounds + no overflow past edges).
Pixel conversion is always explicit at the point of cropping.

## D3 — Templates use base + variant inheritance
**Decision:** A document family has a `base.yaml` plus `variants/*.yaml` that declare `inherits:` and only
`overrides:` / `add_fields:`. See `templates/axis_max/`.
**Why:** Variants (e.g. Premier vs Secure) share most fields; duplicating the full schema per variant is
error-prone. Inheritance keeps the shared schema in one place.
**Consequences:** The loader must resolve inheritance (merge base + overrides) into a flat `Template` before
anything downstream uses it. This is the first real module to build.

## D4 — Engines are pluggable via enums; concrete picks deferred
**Decision:** OCR engine (`OCREngine`: paddle/trocr/tesseract/easyocr), registration method
(`RegistrationMethod`: orb/sift/akaze/manual), validators, export formats are all enum-selected.
**Why:** Avoid locking the system to one OCR/registration library before testing on real docs. Keep each
swappable behind a common interface.
**Consequences:** OCR engine choice is made at the OCR-module session, not now. Each engine needs an adapter
to the common `OCRResult` contract.

## D5 — ROI coordinates captured via a GUI annotator
**Decision:** Field box coordinates are captured by a GUI tool (`tools/roi_annotator.py`): click boxes on a
reference image, auto-write normalized coords into the template YAML.
**Why:** Hand-entering coordinates is tedious and error-prone; a VLM-proposed approach is deferred with the
rest of the AI track. A click-to-annotate tool is the fastest reliable path to usable templates.
**Consequences:** Annotator is roadmap module #2 (right after the loader). Until ROIs exist, nothing past
registration can run.

## D6 — Build the deterministic template track end-to-end first
**Decision:** Complete Phase 1 (template-match path) end-to-end on one real PDF and test it before starting
Phase 2 (VLM fallback + auto-template generation).
**Why:** The deterministic path is simpler and fully testable; the VLM path is more complex and its provider
isn't chosen yet. Proving the spine end-to-end de-risks the rest.
**Consequences:** No VLM code until Phase 1 hits its milestone (one PDF → verified export).

## D7 — VLM provider undecided
**Decision:** The VLM provider for the unknown-doc path is not chosen (pending the owner's manager). Keep it
behind an interface; assume nothing concrete.
**Why:** Organizational decision still open; committing now risks rework.
**Consequences:** Phase 2 design must be provider-agnostic. Revisit and add a superseding entry once decided.

## D8 — Minimal comments; learning notes live in Obsidian, not the repo
**Decision:** Deployment-grade code with minimal comments and no teaching docstrings. Conceptual explanations
("why frozen", "why normalized") are kept in the owner's Obsidian vault, not in source files. The original
`my_understanding.*` notes and teaching comments were migrated out and removed from the repo.
**Why:** Keeps the production codebase clean while preserving the learning trail somewhere better suited to it.
**Consequences:** New code adds comments only where genuinely non-obvious. No `my_understanding.*` files
(also gitignored). The `.claude/` docs carry project-level rationale; Obsidian carries personal learning notes.

## D9 — Templates are self-contained; no shared schema-join YAML
**Decision:** Every field's full metadata (`id, label, datatype, widget, roi, ocr, validation, export`) lives
inline in the template YAML (`base.yaml` + `variants/*.yaml`). Supersedes the open question in D3 / the
template-loader spec. The `templates/schema/*.yaml` placeholder files (`field_types`, `validation`, `widgets`,
`extraction_methods`, `schema`) are removed — they were never populated.
**Why:** A template should fully describe its own extraction without requiring 4-5 auxiliary files to
understand one field. Duplication saved by sharing field metadata is small; loader complexity (join logic)
and cross-file lookups to understand a single field are not worth it. Different templates may legitimately
need different OCR engines/validators for the same semantic field id, so global definitions would need an
override mechanism anyway — self-contained avoids that entirely.
**Consequences:** Only `enums.py` (FieldType, ValidatorType, OCREngine, FieldWidget, etc.), validator
implementations, and OCR engine implementations are shared/reusable across templates — never YAML field
metadata. The loader becomes a straight YAML → dataclass deserializer plus base+variant inheritance merge; no
schema-join step. `FieldConfig` gained a `widget: FieldWidget` field; `SectionConfig.name` renamed to
`SectionConfig.id` (matches the YAML `id` key) and gained `repeatable: bool = False`, `max_items: int | None
= None` to support the `nominee` section.
**Field-id uniqueness:** ids must be unique template-wide (not just per-section) — the loader fails fast on
duplicates. The pre-existing `base.yaml` had `insured_name` duplicated between `applicant_details` (p1) and
`signatures` (p2, the printed name beside the signature); the p2 copy is renamed `insured_signature_name`.

## D10 — Template-level gaps closed while building the loader
**Decision:** Building the loader surfaced that `Template` requires `registration: RegistrationConfig` and
`preprocessing: PreprocessingConfig`, and `TemplateMetadata.version` had no source — none of these existed in
`base.yaml`. Also `TemplateMetadata` had no fields for `issuer`/`document_type`, which `base.yaml`'s
`metadata:` block already carried. Closed both gaps rather than blocking: `TemplateMetadata` gained `issuer:
str` and `document_type: str` (required, validated non-empty like the other identity fields);
`base.yaml`'s top level gained `metadata.version: "1.0"`, `metadata.variant: Base`, a `registration:` block
(`method: orb`, `reference_images: {}`), and a `preprocessing:` block (all five flags `true`).
**Why:** `RegistrationMethod`/engine choice is still deliberately deferred (D4) — `orb` here is a
placeholder, not a commitment, swappable when the `registration/` module is actually built.
`reference_images: {}` is empty because the `.docx` → image render step doesn't exist yet (see
architecture.md cross-cutting notes); it's a known gap, not an oversight, and must be filled before
`registration/` can run. Preprocessing flags default to `true` (standard scan cleanup) and are template-wide
since cleanup needs don't vary per field.
**Consequences:** Variant YAMLs don't repeat `registration:`/`preprocessing:` — they're inherited from base
wholesale (no per-variant override support added, since nothing currently needs one). Revisit the `orb`
placeholder and empty `reference_images` when the registration module lands.

## D11 — ROI annotator: docx2pdf + pdf2image render, Tkinter GUI
**Decision:** `tools/roi_annotator.py` renders each variant's `.docx` reference (Premier and Secure have
*different* source docs — `templates/axis_max/reference/GCL Premier_LFQ 1.docx` vs `GCL Secure_LFQ.docx`) to
PNG via `docx2pdf` (drives local MS Word over COM → PDF) + `pdf2image` (drives `pdftoppm`, found via the
existing MiKTeX install), cached at `templates/axis_max/reference/rendered/<template_id>/page_N.png`. GUI is
stdlib Tkinter: click-drag a box per field on the reference image, normalized to `[0,1]` on release, written
straight into the relevant YAML file. Each variant YAML gained `metadata.reference_docx` (relative path to
its `.docx`) so the annotator knows which file to render per variant.
**Why:** No LibreOffice on this machine (checked — not on PATH or in either Program Files); MS Word and
`pdftoppm` both already present, so this path needs zero new system installs, only 3 new pip packages
(`docx2pdf`, `pdf2image`, `pillow`). Tkinter avoids a heavier GUI dependency (PyQt/PySide) for a one-off
internal annotation tool. Because each variant has its own reference doc, `registration.reference_images`
must be variant-specific — the loader's `_resolve_variant` was extended so a variant's own `registration:`
key, if present, fully replaces (not merges with) base's.
**Consequences:** `docx2pdf`/`pdf2image`/`pillow` added to `requirements.txt`. Running the annotator pops a
visible MS Word window during the first render of each variant (COM automation) — expected, not a bug.
Annotating either variant's shared (base) fields also fills them for the other variant, since both write
into the same `base.yaml`; only each variant's own 1-2 added fields need a separate pass. The annotator
itself was smoke-tested (render pipeline, page→field queue, path resolution) but **not run end-to-end by a
human** — no field has a captured ROI yet as of this entry.

## D12 — Full pipeline built; routing, OCR, and VLM contracts locked
**Decision:** Built both extraction tracks end-to-end (owner's golden pipeline overrides any earlier doc).
The routing brain (`registration/router.py`) decides per document:
- match the scanned page-1 against every registered template's reference image (ORB/SIFT/AKAZE feature
  match + RANSAC homography → inlier ratio `score`);
- **template-match path** iff best `score ≥ REGISTRATION_MATCH_THRESHOLD` AND `num_inliers ≥
  REGISTRATION_MIN_INLIERS` AND the template is annotated (`annotated_fraction ≥ 0.5`, i.e. enough fields have
  ROI coords);
- otherwise **VLM-fallback**: a `VLMProvider` derives structure + normalized bounding boxes, a template is
  auto-generated (`vlm/template_builder.save_generated_template` writes a self-contained `base.yaml` under a
  new family + saves the scanned pages as reference images), the registry reloads, and extraction proceeds
  down the template path on the freshly-saved template. So the next similar doc takes the cheap deterministic
  route — this is the token-reduction goal.
**Extraction is always OCR, never the VLM** — the VLM only proposes geometry/structure. OCR runs per-ROI-crop.
**OCR is pluggable** (`OCREngineAdapter`): `stub` (deterministic, default, no deps — used by every test and
the offline demo) plus lazy real adapters `tesseract`/`easyocr`/`trocr`/`paddle`; engine chosen via
`OCR_ENGINE`. `trocr` (microsoft/trocr-base-handwritten) is the intended quality pick for these handwritten
forms; `easyocr` the general fallback. Real engines live in `requirements-optional.txt`, not core, so a clean
clone installs and tests green without torch/paddle. Added `OCREngine.STUB`.
**VLM is provider-agnostic** (D7 still open): `fake` (deterministic, offline, the only tested provider) plus
lazy `anthropic` (default model `claude-sonnet-4-6`) and `openai` (`gpt-4o`) adapters, selected via
`VLM_PROVIDER`, keyed from `.env`. A shared JSON contract (`vlm/prompt.py`) defines the derived-structure
schema both real providers must return.
**Why fake/stub defaults:** the VLM provider is undecided and no key exists, and heavy OCR deps can't be
assumed installed; deterministic fakes let the entire spine be tested and demoed offline while the real
adapters stay wired behind one env var each.
**Consequences:** core deps grew (`numpy`, `opencv-python-headless`, `openpyxl`, `python-dotenv`); heavy
engine/provider deps are opt-in via `requirements-optional.txt`. `ExportFormat.EXCEL` added (openpyxl).
`load_all_templates` added to load both variant-based families and base-only auto-generated families.
Confidence = `0.5·ocr_confidence + 0.5·validation_score`. Tests use synthetic textured images (so ORB finds
features), stub OCR, and the fake VLM — no confidential `scanned_docs/`/`proper_docs/` data in the suite.
Smoke-tested on a real `scanned_docs/*.pdf`: first run routed VLM-fallback + generated a template, second run
routed template-match with score 1.0.
