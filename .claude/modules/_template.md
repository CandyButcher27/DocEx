# Module: <name>

Copy this file to `modules/<name>.md` when starting a module. Fill each section. Link it from `status.md`.

## Goal
One sentence: what this module is responsible for, and what it is explicitly *not*.

## Inputs
What it consumes (types, files, config objects) and where they come from.

## Outputs
What it produces (types, files) and who consumes them. State the contract precisely — downstream modules
depend on it.

## Dependencies
Modules / libraries this relies on. Note anything that must exist before this can be built.

## Design decisions (this module)
Choices made while building, with the why. Promote anything architecture-wide to [../decisions.md](../decisions.md).

## Open questions
Unresolved items. Flag anything that blocks a later module.

## Tests
What `tests/` covers for this module, and the one real example used to smoke-test it.
