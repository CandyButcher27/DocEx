from __future__ import annotations

from pathlib import Path

import yaml

from .config import TEMPLATE_STORE
from .models import Template


def load_templates(store: Path = TEMPLATE_STORE) -> list[Template]:
    out: list[Template] = []
    for f in sorted(Path(store).glob("*.yaml")):
        out.append(Template.from_dict(yaml.safe_load(f.read_text(encoding="utf-8"))))
    return out


def save_template(template: Template, store: Path = TEMPLATE_STORE) -> Path:
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{template.template_id}.yaml"
    path.write_text(
        yaml.safe_dump(template.to_dict(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def get_template(template_id: str, store: Path = TEMPLATE_STORE) -> Template | None:
    path = Path(store) / f"{template_id}.yaml"
    if not path.exists():
        return None
    return Template.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))
