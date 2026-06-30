# Status — where to pick up

**Update this every session.** It is the first thing a fresh session reads to know what is done and what is next.

Phase: **1 — deterministic template-match track.** Next module: **`template/` loader + parser + registry.**

## Module states

| Area | Module | State | Next action |
|---|---|---|---|
| Data | `src/models/` (roi, ocr_result, validation_result, field) | ✅ done | `document.py`, `page.py`, `models/template.py` still empty — fill when pipeline needs them |
| Config | `src/template/` config dataclasses + enums | ✅ done | — |
| Config | `src/template/` loader + parser + registry | ⬜ empty | **BUILD NEXT** — YAML (base+variant) → `Template` objects. Spec: [modules/template-loader.md](modules/template-loader.md) |
| Templates | `templates/axis_max/` base + variants | ⚠️ partial | schema present but **no ROI coordinates** — needs the annotator |
| Templates | `templates/schema/*.yaml` | ⚠️ partial | several files empty (`schema.yaml`, `field_types.yaml`, `extraction_methods.yaml`) |
| Tools | `tools/roi_annotator.py` | ⬜ empty | build after loader (#2) — GUI to write ROI coords into YAML |
| Pipeline | `src/preprocessing/` | ⬜ empty | PDF→image + clean (#3) |
| Pipeline | `src/registration/` | ⬜ empty | match + align (#4) |
| Pipeline | `src/roi/` | ⬜ empty | crop regions (#5) |
| Pipeline | `src/ocr/` | ⬜ empty | OCR per crop (#6); engine pluggable, pick here |
| Pipeline | `src/validation/` + `src/confidence/` | ⬜ empty | validate + score (#7) |
| Pipeline | `src/exporters/` | ⬜ empty | JSON/CSV/Excel (#8) |
| Pipeline | `src/pipeline/` | ⬜ empty | orchestrate end-to-end (#9) |
| Support | `src/configs/`, `src/utils/` | ⬜ empty | fill as needed |
| Tests | `tests/` | ⚠️ partial | model tests only (roi, field, ocr_result, validation_result); add per-module tests as modules land |

Legend: ✅ done · ⚠️ partial · ⬜ empty

## Immediate next step
Build `src/template/loader.py` + `parser.py` + `registry.py`: load `axis_max/base.yaml`, resolve the
`premier_lfq` / `secure_lfq` variant inheritance, and produce a flat `Template` object. Read the existing
config dataclasses in `src/template/` first (they define the target shape). See [modules/template-loader.md](modules/template-loader.md).
