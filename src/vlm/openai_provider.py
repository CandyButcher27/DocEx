import numpy as np

from .base import VLMProvider
from .prompt import INSTRUCTION, extract_json, parse_derived_document
from .schema import DerivedDocument
from ._image import encode_png_b64

_DEFAULT_MODEL = "gpt-4o"


class OpenAIVLMProvider(VLMProvider):

    name = "openai"

    def __init__(self, api_key: str, model: str = "") -> None:
        from openai import OpenAI

        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai VLM provider.")

        self._client = OpenAI(api_key=api_key)
        self._model = model or _DEFAULT_MODEL

    def derive_structure(self, images: list[np.ndarray], family_hint: str | None = None) -> DerivedDocument:
        content: list[dict] = [{"type": "text", "text": INSTRUCTION}]
        for image in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{encode_png_b64(image)}"},
                }
            )

        if family_hint:
            content.append({"type": "text", "text": f"Suggested family name: {family_hint}"})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
        )

        text = response.choices[0].message.content or ""
        return parse_derived_document(extract_json(text))
