# Document_Extractor — session entry point

Read this first. It orients you, then points you to the right doc.

## What this project is
A document extraction pipeline. Scanned documents (PDFs in `scanned_docs/`) come in. Each is matched
against known **templates** (reference layouts in `proper_docs/`). Two paths:

- **Template-match path (deterministic):** doc matches a known template → align page → crop each field's
  region (ROI) → OCR each crop → validate → export (JSON/CSV/Excel).
- **VLM-fallback path:** no template matches → a VLM derives the document structure → OCR extracts the
  fields → export → **the derived structure is auto-saved as a new template** so the next similar doc
  takes the cheap deterministic path.

## Current phase
**Phase 1 — build the deterministic template-match track end-to-end** on one real PDF, then test it.
The VLM/auto-template track (Phase 2) comes only after Phase 1 works. See [roadmap.md](roadmap.md).

## How this project is built
Module by module, across separate sessions. Each session discusses *what / why / what decisions* for one
module. Do **not** one-shot the pipeline. The owner is learning the system as it is built.

## Golden rules for any session
1. **Minimal comments.** This is deployment-grade code. No teaching comments, no docstrings unless asked.
   Conceptual/learning notes go to the owner's Obsidian vault, not into the repo. See [conventions.md](conventions.md).
2. **Keep the docs in sync.** If you change a module, update [status.md](status.md). If you make or change
   an architectural decision, append to [decisions.md](decisions.md). Never let these drift from the code.
3. **Respect the build order.** Don't jump ahead to a later module or to Phase 2.
4. **Read before you write.** Read the consumer of any output you produce (parser before prompt, caller
   before function) — see the owner's global failure rules.
5. **Smoke-test on one example before scaling.**

## Doc index
- [architecture.md](architecture.md) — canonical reference: pipeline, the two paths, data model, module I/O contracts.
- [decisions.md](decisions.md) — log of locked decisions and their rationale (append-only).
- [status.md](status.md) — module-by-module build state and the next action. **Start here to know where to pick up.**
- [roadmap.md](roadmap.md) — phased build order and milestones.
- [conventions.md](conventions.md) — env, testing, comment policy, git workflow, how to update these docs.
- [modules/](modules/) — per-module deep specs (created as each module is tackled).
