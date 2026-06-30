# Conventions

## Environment
- Windows 11 host. Native context: PowerShell, paths `C:\Users\sriva\...`. WSL context: bash, `/mnt/c/...`.
- Python 3.11+. Always run inside the project `.venv`. If absent: `python -m venv .venv`.
- Detect context from the platform line in the system prompt (win32 vs linux).

## Code style
- **Minimal comments.** Deployment-grade. No teaching comments, no docstrings unless explicitly asked.
- Conceptual / learning explanations go to the owner's **Obsidian vault**, never into source files.
- **No `my_understanding.*` files** in the repo (also gitignored). They were migrated to Obsidian and removed.
- Python 3.11+ idioms. Type hints throughout. `frozen, slots` dataclasses for config/result objects (see decisions D1).
- No unused imports/variables, no dead code. Prefer flat, simple code over premature abstraction.
- Comment only where genuinely non-obvious (a surprising workaround, a non-trivial invariant).

## Testing
- pytest. Every module gets its own test file under `tests/`.
- Add/update tests for non-trivial logic (parsers, inheritance resolution, registration math, validators).
  Skip for trivial edits (renames, reformat).
- **Smoke-test on one real example before scaling** any batch run, using the same flags as the full run.
  Verify the output yourself; don't ask the owner to verify.

## Git workflow
- Feature work on a branch: `git checkout -b feat/<short-desc>`. Conventional commits (`feat:`/`fix:`/`refactor:`/`test:`/`docs:`), subject ≤50 chars.
- Small, deliberate commits that tell a story. Never batch unrelated changes.
- **Confirm before** `git commit`, `git push`, opening/merging a PR, or deleting files/branches.
- No `Co-Authored-By` / AI authorship lines in commit messages.

## Keeping the `.claude/` docs in sync
- Changed a module's state? Update [status.md](status.md).
- Made or changed an architectural decision? Append an entry to [decisions.md](decisions.md) (never overwrite history).
- Changed how stages connect or a module's I/O? Update [architecture.md](architecture.md).
- Starting a new module? Create `modules/<name>.md` from [modules/_template.md](modules/_template.md) and link it from `status.md`.
- These docs are the contract between sessions. If they drift from the code, the module-by-module workflow breaks.
