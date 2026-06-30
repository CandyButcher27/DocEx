# IDP Engine — Design & Implementation (demo-main)

Intelligent Document Processing engine implementing the v1 architecture in
`IDP_Architecture_v1.md`. Built in two phases:

- **Phase 1 (deterministic):** local OCR ensemble + anchor-relative ROI extraction +
  rule-based decision engine. Fully offline. A stub stands in for the VLM.
- **Phase 2 (VLM, current):** a real cloud **Vision-Language Model** (Gemini, pluggable)
  now does two jobs — (a) **reads hard/handwritten field values** the OCR stack can't,
  and (b) **detects the format of an unknown document**, deriving its fields so a new
  template is auto-cached. Provider + key come from `.env`; `VLM_PROVIDER=fake` keeps
  the whole engine offline for tests.

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
- **decision engine** — fuses the per-field VLM candidate (one batched call/doc) with
  the OCR ensemble candidates. The VLM is **authoritative for handwriting**: if its
  value passes validation it wins (source `vlm`); otherwise fall back to OCR consensus
  (source `ocr`); anything still weak is flagged (`pending_human`). Human answers come
  back as source `human`, confidence 1.0.
- **vlm (`idp/vlm.py`)** — `VLMClient` interface, providers `gemini` | `ollama` | `fake`.
  Two methods, **one cloud call each per document**:
  - `extract_fields(page, fields)` → reads every field value from the full page in a
    single JSON response (rate-friendly, and the model sees full context, not tiny crops).
  - `detect_format(page)` → derives the field list (label, value direction, datatype)
    for an unknown layout, which is turned into a template and cached.
  Keys are read from `.env`; the key is never logged or committed.
- **report (`idp/report.py`)** — renders a self-contained `report.html` (images inlined
  as base64): summary cards, the full field table with status / value / confidence /
  source / ROI thumbnail, the human-review queue, and the annotated page overlay.

## Output
`output/<doc>/result.json` — per-field `{value, confidence, source, validated, status}`,
a `review_queue`, classification detail, and run metadata. ROI crops in
`output/<doc>/crops/`, plus an `annotated.png` overlay (green=accepted, red=review).

## Demo results (two end-to-end runs, HTML reports in `output/<doc>/report.html`)

**Test 1 — known template, `925060052530917.pdf`.** Classified `axis_gcl_premier_lfq`
via the text path (coverage 0.875; phash correctly abstained — the scan is a different
layout variant of the same form). The deterministic OCR stack alone auto-accepts very
little because the values are **handwritten**; with the VLM fused in, **18/20 fields
auto-accept** (source `vlm`) — loan a/c 925060052530917, name ANUJ KUMAR, DOB 29-02-1981,
city BANGALORE, PIN 560098, etc. The 2 genuinely blank fields go to human review.

**Test 2 — completely unseen doc, `PPR005312996838.pdf`** (a *different* form: Group
Credit Life Senior OPDA). No template matches (coverage 0.5 < 0.6). The VLM
**`detect_format` derives 40 fields** from the page, a new template is cached
(`template_store/vlm_PPR005312996838.yaml`), and extraction then runs on it:
**28/40 auto-accept** — loan a/c PPRD05312996838, name SHARIO NAWAZ, DOB 15-08-1987,
PAN, sum assured 550000, etc. The next Senior-OPDA doc would take the cheap template
path with no `detect_format` call.

Both alternate paths are also unit/integration verified: VLM-authoritative decision,
fake-VLM offline mode, and human-apply (review → `accepted / source=human`).

Honesty note: a few low-value fields can still slip through on OCR agreement or a VLM
misread (e.g. a stray `payee_bank='7'`). These surface in the report with their source
and confidence; they are not hidden.

## Privacy
- **Local-only stages:** rendering, OCR ensemble, classification, ROI, validation,
  decision, reporting. With `VLM_PROVIDER=fake` the whole engine runs offline.
- **Cloud stage (opt-in):** the VLM. The page image is sent to the configured provider
  (here Gemini) for value reading / format detection — the architecture's original
  "local VLM" slot, swapped for a cloud VLM at the owner's instruction. Swapping in a
  local VLM (Qwen2-VL / MiniCPM-V) behind the same `VLMClient` interface restores full
  offline operation with no other code change.
- **Version control:** `.env`, `scanned_docs/`, `proper_docs/`, all `*.docx`, and
  `output/` are gitignored — the API key, customer documents, and extracted PII never
  enter git. Only code and the (PII-free) template YAML are committed.

## Run
```
# .env holds VLM_PROVIDER + the provider key (gemini here). Not committed.
python tools/build_gcl_template.py                     # build + cache the GCL template
python -m idp.cli scanned_docs/925060052530917.pdf --html   # known template  -> report.html
python -m idp.cli scanned_docs/PPR005312996838.pdf --html   # unseen -> VLM learns -> report.html
pytest tests/test_idp_engine.py                        # 22 unit/integration tests
```
Each run writes `output/<doc>/`: `result.json`, ROI `crops/`, `annotated.png`, and
(`--html`) a self-contained `report.html`.

External dependency: Ghostscript (`gswin64c`) on PATH. Python deps in
`requirements-demo.txt`. DOCX template building also needs MS Word (docx2pdf).
