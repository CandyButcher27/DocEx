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
