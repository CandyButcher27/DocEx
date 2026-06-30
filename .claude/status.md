# Status — where to pick up

**Update this every session.** It is the first thing a fresh session reads to know what is done and what is next.

Phase: **Both tracks built end-to-end** (template-match + VLM-fallback + auto-template gen). Pipeline runs on a
real scanned PDF with the offline defaults (`OCR_ENGINE=stub`, `VLM_PROVIDER=fake`). Next: **plug in a real OCR
engine + real VLM provider** (add keys to `.env`, install from `requirements-optional.txt`) and tune the
registration threshold on real docs.

## Module states

| Area | Module | State | Next action |
|---|---|---|---|
| Data | `src/models/` (roi, ocr_result, validation_result, field, page, document) | ✅ done | `models/template.py` still empty — unused |
| Config | `src/template/` dataclasses + enums | ✅ done | `OCREngine.STUB` + `ExportFormat.EXCEL` added |
| Config | `src/template/` loader + parser + registry | ✅ done | `load_all_templates` scans every family (variants or base-only auto templates) |
| Templates | `templates/axis_max/` base + variants | ⚠️ partial | 90 self-contained fields — **no ROI coords yet** (annotated_fraction 0 → routes to VLM until annotated or a real VLM derives them) |
| Tools | `tools/roi_annotator.py` | ✅ built, ⬜ unrun | manual ROI capture path; optional now that VLM can auto-derive ROIs |
| Config | `src/configs/settings.py` | ✅ done | env-driven (`.env`); `get_settings()` cached |
| Pipeline | `src/preprocessing/` | ✅ done | `pdf_to_images` + `clean_image` (deskew/denoise/CLAHE/adaptive-threshold) |
| Pipeline | `src/registration/` | ✅ done | ORB/SIFT/AKAZE matcher + aligner + `route_document` (the routing brain) |
| Pipeline | `src/roi/` | ✅ done | `crop_page_fields` — normalized ROI crops, skips unannotated |
| Pipeline | `src/ocr/` | ✅ done | pluggable: stub (default/tests) + lazy tesseract/easyocr/trocr/paddle adapters + factory |
| Pipeline | `src/validation/` + `src/confidence/` | ✅ done | per-`ValidatorType` normalize+validate; confidence = 0.5·ocr + 0.5·validation |
| Pipeline | `src/exporters/` | ✅ done | JSON / CSV / Excel |
| Pipeline | `src/pipeline/` | ✅ done | `extract_document` orchestrates both routes; `extract.py` CLI |
| VLM | `src/vlm/` | ✅ done | provider-agnostic (fake/anthropic/openai) + auto-template generation from derived structure |
| Tests | `tests/` | ✅ done | 77 passing incl. end-to-end pipeline (VLM-fallback bootstrap → template-match on re-run) |

Legend: ✅ done · ⚠️ partial · ⬜ empty

## Immediate next step
The spine works on the offline defaults and was smoke-tested on a real `scanned_docs/*.pdf` (route VLM →
template generated → second run routes template-match, score 1.0). To make it production-real:
1. Pick + install a real OCR engine (`requirements-optional.txt`); set `OCR_ENGINE` in `.env`. For handwritten
   forms `trocr` is the quality pick, `easyocr` the general one.
2. Pick a VLM provider once decided (D7 still open); set `VLM_PROVIDER` + key in `.env`. The Anthropic/OpenAI
   adapters are wired and lazy; only the `fake` provider is tested.
3. Tune `REGISTRATION_MATCH_THRESHOLD` / `REGISTRATION_MIN_INLIERS` against real scans.
4. Optionally run `tools/roi_annotator.py` to hand-annotate `axis_max` instead of letting the VLM derive it.
