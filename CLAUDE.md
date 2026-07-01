# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A document field-extraction pipeline: scanned/uploaded PDFs (or PNG/JPG, auto-converted) go through OCR, and an LLM reads the OCR output to pull out user-specified fields (e.g. "Policy Number", "Date of Birth") as `{field: value}` pairs, downloadable as CSV. There are two parallel workflows in this repo — a **template-authoring tool** (draw field boxes on a clean template) and a **runtime extraction UI** (upload a real scanned doc, get field values out). They are not yet wired together; the runtime extractor currently OCRs the whole page and asks the LLM to find fields by name, not by the template's stored coordinates.

## Running things

No test suite, no build step, no lint config — this is a set of standalone Python scripts with local HTTP servers, run directly.

```powershell
# always run inside the venv
.venv\Scripts\python.exe <script>.py
```

- **Extraction UI** (main deliverable): `python extract_ui.py` → `http://localhost:8002`. Upload a PDF/PNG/JPG, add fields with `+`, hit Extract, watch OCR → LLM progress, view results table, download CSV.
- **Template field-authoring tool**: `python template_tool.py` → `http://localhost:8001`. Pick a template from `proper_docs/` (docx auto-converted to PDF via Word COM, cached in `proper_docs_pdf/`), draw a box per field, name it, set type (string/number/checkbox/date/alphanumeric) and required flag. Saves to `templates/<template_name>.yaml`.
- **Crop tool** (early prototype, scanned_docs only): `python crop_tool.py` → `http://localhost:8000`. Draws + saves single crops to `cropped_images/`.
- **Standalone OCR scripts** (engine comparison / one-off use, not wired into the UIs): `paddle_ocr.py`, `rapidocr_run.py`, `tesseract_run.py`, `run_trocr.py` — each reads a folder of cropped images (`test_crop/` or `cropped_images/`) and writes a JSON of `{text, avg_confidence, ...}` per file. `paddle_page_ocr.py` and `overlay_boxes.py` are page-level (not crop-level) equivalents: the former OCRs a whole rendered page image into a bbox-annotated JSON, the latter draws a template's stored yaml boxes onto a scanned page image so you can visually check alignment drift.

All three local servers use the same pattern: stdlib `http.server.BaseHTTPRequestHandler`, no framework (Flask/FastAPI are not installed — don't add them without asking). Each serves its own `.html` frontend at `/` and JSON/PNG over a handful of `GET`/`POST` routes. Multipart file uploads are hand-parsed (`parse_multipart` in `extract_ui.py`) rather than using `cgi` (deprecated) or a form library.

## Architecture

**`extract_ui.py` / `extract_ui.html`** — the runtime pipeline:
1. `/upload` — accepts PDF or image (PNG/JPG auto-converted to a single-page PDF via Pillow, `image_bytes_to_pdf_bytes`). Stores per-doc state in the in-memory `DOCS` dict keyed by `doc_id` (not persisted — restarting the server loses all uploaded docs).
2. `/run_ocr` — renders every page via `pdf2image.convert_from_path` at `DPI = 150`, runs `PaddleOCR` (`use_doc_orientation_classify/unwarping/textline_orientation` all disabled — the OCR is not correcting skew/rotation, see note below) on each page, returns line count. OCR entries (`text`, `confidence`, `bbox`, `page`) are cached on the doc, not returned to the client.
3. `/run_llm` — sends the full OCR entry list plus the user's field-name list to `llm_client.run_extraction`, using `EXTRACTION_PROMPT` (asks for a plain `{field: value}` JSON, `"NOT_FOUND"` if absent). Response is regex-extracted (`\{.*\}`) and JSON-parsed defensively.

**`llm_client.py`** — thin wrapper around Ollama Cloud's OpenAI-compatible endpoint (`OLLAMA_BASE_URL=https://ollama.com/v1`, no `openai` SDK dependency, just `requests`). Config comes from `.env` (`OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` — currently `gpt-oss:120b`, chosen for reliable structured-JSON output over the previous `gemma4:31b`). `run_extraction(ocr_json, prompt, model=...)` is the one entry point other scripts call.

**`template_tool.py` / `template_tool.html`** — authoring tool for per-template field definitions. Converts `proper_docs/*.docx` to PDF via `docx2pdf` (needs MS Word installed — Windows COM automation, not portable). Saves field boxes as fractional (0–1) `{x, y, w, h}` coordinates plus `name`/`type`/`required`/`page` to `templates/<name>.yaml`. These yaml files are the intended source of truth for "where is field X on this document" but **are not currently consumed by `extract_ui.py`** — the runtime path re-discovers fields by name via the LLM reading raw OCR text, not by looking up template coordinates.

**Known gap discovered via `overlay_boxes.py`**: template yaml coordinates are fractional/percentage-based and only line up correctly with a scan if the scan has the same crop/aspect/rotation as the clean template. Real scans have skew and scan-bed margins that clean docx renders don't, so directly reusing template boxes on a scan requires either deskew/registration or anchor-relative extraction (locate boxes via OCR'd label text + stored offset) — neither is implemented yet.

## Known constraints / things not to "fix" without asking

- **`enable_mkldnn=True` crashes** on this machine's PaddlePaddle build (`NotImplementedError: ConvertPirAttribute2RuntimeAttribute ... onednn_instruction.cc`). Keep it `False` in every `PaddleOCR(...)` call. This was tested and reverted — don't re-enable it as a "speed fix" without expecting the same crash.
- **PaddleOCR is CPU-only, single global engine instance** (`_ocr_engine` module global in `extract_ui.py`, lazy-loaded on first request). Cold start (model load) costs ~15–30s once per server process; OCR itself is the dominant cost and scales with page count and text density (a dense single page can take minutes on a weak CPU). A section-based-OCR + thread-pool-worker design (draw big regions, OCR only those, parallel workers capped at `min(3, num_sections)`) was prototyped and reverted per user request — if revisited, check `git show 55bb338` as the last-known-good baseline to diff against, and be aware sharing one `PaddleOCR` instance across threads was assumed unsafe (the prototype used a small pool of separate engine instances instead).
- **`.env` holds real API keys** (`OLLAMA_API_KEY`, `GEMINI_API_KEY`) — already gitignored, never print full values, never commit.
- `proper_docs/` (real customer forms) and `templates/**/reference/` are gitignored — confidential source documents, don't try to commit or publish them.
- `scanned_docs/` is also gitignored (test scans) — safe to use locally for testing but don't assume it's tracked in git.
