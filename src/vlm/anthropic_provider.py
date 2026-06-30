import numpy as np

from .base import VLMProvider
from .prompt import INSTRUCTION, extract_json, parse_derived_document
from .schema import DerivedDocument
from ._image import encode_png_b64

_DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicVLMProvider(VLMProvider):

    name = "anthropic"

    def __init__(self, api_key: str, model: str = "") -> None:
        import anthropic

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the anthropic VLM provider.")

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or _DEFAULT_MODEL

    def derive_structure(self, images: list[np.ndarray], family_hint: str | None = None) -> DerivedDocument:
        content: list[dict] = [{"type": "text", "text": INSTRUCTION}]
        for image in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": encode_png_b64(image),
                    },
                }
            )

        if family_hint:
            content.append({"type": "text", "text": f"Suggested family name: {family_hint}"})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )

        text = "".join(block.text for block in response.content if block.type == "text")
        return parse_derived_document(extract_json(text))
