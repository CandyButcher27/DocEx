import json
from pathlib import Path

ROOT = Path(__file__).parent
REGISTRY_FILE = ROOT / "data" / "doc_type_registry.json"

_registry = None
_spec_cache = {}


def load_registry():
    global _registry
    if _registry is None:
        _registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return _registry


def resolve(doc_kind):
    """Look up a doc_kind (as returned by ingest_gate.match_template) in the registry.
    Returns {"spec": [...], "include_medical": bool} or None if doc_kind is unregistered
    (callers should fall back to field_extractor's universal default spec in that case)."""
    entry = load_registry().get(doc_kind)
    if entry is None:
        return None
    spec_path = entry["field_spec_path"]
    if spec_path not in _spec_cache:
        _spec_cache[spec_path] = json.loads((ROOT / spec_path).read_text(encoding="utf-8"))
    return {"spec": _spec_cache[spec_path], "include_medical": entry["include_medical"]}
