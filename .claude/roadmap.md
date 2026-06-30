# Roadmap

Two phases. Finish Phase 1 end-to-end and test it on a real PDF before touching Phase 2. (Decision D6.)

## Phase 1 — Deterministic template-match track (DO FIRST)

Goal: make one `scanned_docs/*.pdf` flow all the way to an exported file, matched against an `axis_max`
template. Build in this order — each module's output feeds the next (contracts in [architecture.md](architecture.md)):

1. **`template/` loader + parser + registry** — YAML (base + variant inheritance) → flat `Template` objects;
   index them in a registry. *(next session)*
2. **`tools/roi_annotator.py`** — GUI to capture normalized field coordinates onto the reference image and
   write them into the template YAML. *Templates are unusable downstream without ROIs.*
3. **PDF loader + `preprocessing/`** — PDF → page images; deskew / denoise / binarize.
4. **`registration/`** — match the scanned page to a template and align it to the reference (ORB/SIFT/AKAZE).
5. **`roi/`** — crop each field's region from the aligned page.
6. **`ocr/`** — run the OCR engine (pluggable; pick the engine here) on each crop → `OCRResult`.
7. **`validation/` + `confidence/`** — normalize, validate, score each field → `ValidationResult`.
8. **`exporters/`** — serialize to JSON / CSV / Excel.
9. **`pipeline/`** — orchestrate 1–8 over one document. Smoke-test on a single real PDF.

**Milestone P1:** one scanned PDF → exported JSON, field by field, verified against its `proper_docs/` reference.

## Phase 2 — VLM / unknown-document track (AFTER P1 works)

1. **Template-match gate** — does the scanned doc match any registered template? (built on registration's matcher).
2. **VLM structure derivation** — on a miss, a VLM infers field structure. Provider undecided (D7) → keep behind
   an interface.
3. **Extract + export** — OCR fills the values; export as in Phase 1.
4. **Auto-template generation** — persist the inferred structure (with ROIs) as a new template so the next
   similar document takes the deterministic path.

**Milestone P2:** an unseen document type extracts via VLM, and a reusable template is saved and picked up on
the next run of a similar doc.
