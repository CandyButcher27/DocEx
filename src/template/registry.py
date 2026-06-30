from .template import Template


class TemplateRegistryError(Exception):
    """Raised on registry misuse (duplicate id, unknown lookup)."""


class TemplateRegistry:

    def __init__(self) -> None:
        self._templates: dict[str, Template] = {}

    def register(self, template: Template) -> None:
        template_id = template.metadata.template_id

        if template_id in self._templates:
            raise TemplateRegistryError(f"Template '{template_id}' is already registered.")

        self._templates[template_id] = template

    def get(self, template_id: str) -> Template:
        if template_id not in self._templates:
            raise TemplateRegistryError(f"No template registered with id '{template_id}'.")

        return self._templates[template_id]

    def by_family(self, family: str) -> list[Template]:
        return [t for t in self._templates.values() if t.metadata.family == family]

    def all(self) -> list[Template]:
        return list(self._templates.values())

    def __len__(self) -> int:
        return len(self._templates)
