# Roadmap

Two phases. Finish Phase 1 end-to-end and test it on a real PDF before touching Phase 2. (Decision D6.)

## Phase 1 — Deterministic template-match track (DO FIRST)

Goal: make one `scanned_docs/*.pdf` flow all the way to an exported file, matched against an `axis_max`
template. Build in this order — each module's output feeds the next (contracts in [architecture.md](architecture.md)):

1. **`template/` loader + parser + registry** — ✅ done. YAML (base + variant inheritance) → flat `Template`
   objects; indexed in a `TemplateRegistry`.
2. **`tools/roi_annotator.py`** — ✅ built (Tkinter, renders `.docx` reference via `docx2pdf`+`pdf2image`,
   click-to-box, writes ROI + `registration.reference_images` back to YAML). **Not yet run** — no field has a
   real ROI. *Templates are unusable downstream without ROIs.* Run it next, before module #3.
3. **PDF loader + `preprocessing/`** — ✅ `pdf_to_images` + `clean_image` (deskew/denoise/CLAHE/threshold).
4. **`registration/`** — ✅ ORB/SIFT/AKAZE matcher + aligner + `route_document` routing gate.
5. **`roi/`** — ✅ `crop_page_fields` (normalized ROI crops).
6. **`ocr/`** — ✅ pluggable adapters (stub default + lazy tesseract/easyocr/trocr/paddle).
7. **`validation/` + `confidence/`** — ✅ per-validator normalize+validate + confidence score.
8. **`exporters/`** — ✅ JSON / CSV / Excel.
9. **`pipeline/`** — ✅ `extract_document` orchestrates end-to-end; smoke-tested on a real PDF.

**Milestone P1:** ✅ a scanned PDF flows to an exported file, field by field. (Values are real once a real OCR
engine replaces the `stub`; geometry is real once `axis_max` is annotated or derived by a real VLM.)

## Phase 2 — VLM / unknown-document track — ✅ built

1. **Template-match gate** — ✅ `route_document` (built on registration's matcher).
2. **VLM structure derivation** — ✅ `VLMProvider` interface, provider-agnostic (D7 still open); `fake` tested,
   `anthropic`/`openai` wired behind env config.
3. **Extract + export** — ✅ OCR fills values down the same template path; export as Phase 1.
4. **Auto-template generation** — ✅ `save_generated_template` persists the derived structure + ROIs + reference
   images as a new template; next similar doc takes the deterministic path.

**Milestone P2:** ✅ smoke-tested — an unknown doc routes to the (fake) VLM, a reusable template is saved, and
the second run of the same doc routes template-match (score 1.0). Swap `VLM_PROVIDER=anthropic|openai` + key
to make it real.

## What's left (real-world hardening, not new architecture)
- Install + select a real OCR engine; tune for the handwritten forms.
- Choose the VLM provider (D7) and validate derived ROIs against real scans.
- Tune registration thresholds on the real `scanned_docs/`.
