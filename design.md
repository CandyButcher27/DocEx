# IDP Engine — Design & Implementation (demo-main)

Offline, privacy-first Intelligent Document Processing engine. Implements the v1
architecture in `IDP_Architecture_v1.md`. Everything runs locally; no cloud OCR, no
network. The **only** simulated component is the VLM, which is a stub (`idp/vlm.py`).

## Goal (unchanged from the architecture)
Not 100% automation. Auto-extract every field the system can verify with high
confidence; route everything uncertain to a human review queue. On a dense,
handwritten form a high review rate is the *correct* outcome, not a failure.

## Pipeline
```
PDF / DOCX / image
  └─ render (Ghostscript / docx2pdf)           idp/render.py
      └─ OCR page pass (RapidOCR)               idp/ocr/
          └─ Template classification            idp/classify.py
              ├─ known  → field extraction
              └─ unknown→ Stub VLM learns + caches a new template   idp/vlm.py, idp/learn path
                  for each field:
                    ROI extraction (anchor-relative)   idp/roi.py
                      └─ OCR ensemble on the ROI crop   idp/ocr/ensemble.py
                          └─ Decision engine            idp/decision.py
                              consensus → validate → VLM arbitration → human flag
  └─ Structured JSON + review queue + ROI crops  idp/pipeline.py, output/<doc>/
```

## Key design decision: anchor-relative ROIs, not absolute bbox + homography
The architecture proposed storing absolute bounding boxes and aligning each scan to
the template. The real data breaks that assumption: the reference (`proper_docs/*.docx`)
is a clean blank form, while the scan (`scanned_docs/*.pdf`) is a **different, denser
layout variant** of the same form family — confirmed by a perceptual-hash distance of
~60 between them. Pixel alignment would be unreliable.

So a template field stores a **printed-label anchor** (e.g. "PAN Number") plus a value
direction (`right` / `below`). At extract time we OCR the page, fuzzy-match the anchor
in the noisy OCR output, then read the value from the adjacent region. This is robust
to layout shifts and to OCR garble (labels come out as "PAN Numbey", "InsureuMember",
etc.). Absolute bbox is still supported in the model for templates that want it.

## Modules
- **render** — Ghostscript (`gswin64c`) for PDF→PNG (reliable, no poppler needed);
  `docx2pdf` (Word COM) for DOCX→PDF→PNG, used only when building a template.
- **OCR ensemble** — pluggable `OCREngine` interface. Real engines: RapidOCR (ONNX,
  offline) + a binarized/upscaled variant voter (genuine second vote on the same
  backend) + optional Tesseract if a binary is present. Page pass locates anchors;
  per-ROI pass re-reads each crop. List-marker artifacts ("14)") are stripped.
- **classify** — perceptual hash (fast path) + signature-phrase coverage (fuzzy,
  sliding-window) as the layout-robust fallback. On this data the phash path correctly
  abstains and the text path matches at 0.875 coverage.
- **templates / store** — YAML per template: id, signature phrases, phash, and field
  specs (anchors, datatype, regex, required, choices). `idp/builder.py` derives
  phash + phrases from the reference and pairs them with authored field specs.
- **roi** — anchor fuzzy-match (`difflib`), then value-region accumulation: walk
  same-line words rightward from the anchor, stop at a column gap, a neighbour
  anchor/known label, or a list marker. Tight union → crop.
- **validate** — regex / datatype / length / required. PAN (`[A-Z]{5}[0-9]{4}[A-Z]`),
  number (rejects digits embedded in label text), date, choice.
- **decision engine** — (1) ensemble consensus, (2) validation, (3) Stub-VLM
  arbitration when engines disagree or confidence is moderate, (4) human flag for the
  rest. Emits source = `ocr` | `vlm_stub` | `human` | `pending_human`.
- **review** — builds the human queue (prediction + confidence + ROI crop + reason)
  and applies human answers back (`source=human`, confidence 1.0).
- **vlm (STUB)** — placeholder for a local VLM. `arbitrate()` picks the
  validation-passing / highest-confidence candidate; `learn_template()` returns a
  cached template shell for unknown layouts. Swapping in a real local VLM
  (e.g. Qwen2-VL / MiniCPM-V) is the only remaining work to lift handwriting accuracy.

## Output
`output/<doc>/result.json` — per-field `{value, confidence, source, validated, status}`,
a `review_queue`, classification detail, and run metadata. ROI crops in
`output/<doc>/crops/`, plus an `annotated.png` overlay (green=accepted, red=review).

## Demo result — `scanned_docs/925060052530917.pdf`
Classified as `axis_gcl_premier_lfq` via the text path (score 0.875; phash correctly
abstained). 20 fields: printed labels are located accurately (see `annotated.png`),
but the field **values are handwritten**, so most route to human review — the intended
human-in-the-loop behaviour. The annotated overlay shows ROIs sitting on the correct
values (PAN, name, sum-assured, policy number). Both alternate paths are exercised and
verified: unknown-template → Stub-VLM learns a new cached template; human-apply flips a
reviewed field to `accepted / source=human`.

A note on honesty: with a *stub* VLM and handwritten input, the deterministic stack
auto-accepts only the cleanest fields and can occasionally agree on a misread. This is
exactly the gap a real VLM arbitrator closes; it is documented rather than hidden.

## Privacy
`scanned_docs/`, `proper_docs/`, all `*.docx`, and `output/` are gitignored — customer
documents and extracted PII never leave the machine or enter version control. Only code
and the (PII-free) template YAML are committed.

## Run
```
python tools/build_gcl_template.py          # build + cache the template from the docx
python -m idp.cli scanned_docs/<file>.pdf   # extract → output/<file>/result.json
pytest tests/test_idp_engine.py             # 19 unit/integration tests
```
External dependency: Ghostscript (`gswin64c`) on PATH. Python deps in
`requirements-demo.txt`. DOCX template building also needs MS Word (docx2pdf).
