from src.configs.settings import Settings

from .base import VLMProvider
from .fake import FakeVLMProvider


def get_vlm_provider(settings: Settings) -> VLMProvider:
    name = settings.vlm_provider

    if name == "fake":
        return FakeVLMProvider()
    if name == "anthropic":
        from .anthropic_provider import AnthropicVLMProvider

        return AnthropicVLMProvider(settings.anthropic_api_key, settings.vlm_model)
    if name == "openai":
        from .openai_provider import OpenAIVLMProvider

        return OpenAIVLMProvider(settings.openai_api_key, settings.vlm_model)

    raise ValueError(f"Unknown VLM provider '{name}'. Known: fake, anthropic, openai.")
