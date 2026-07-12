import os

from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

from app.config import ModelConfig


def create_nvidia_model(model_name: str = "z-ai/glm-5.2"):
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")

    if not nvidia_api_key:
        raise RuntimeError("Missing NVIDIA_API_KEY in your .env file")

    nvidia_client = AsyncOpenAI(
        api_key=nvidia_api_key,
        base_url="https://integrate.api.nvidia.com/v1",
    )

    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=nvidia_client,
    )

def create_gemini_model(model_name: str = "gemini-3.1-flash-lite"):
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not gemini_api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in your .env file")

    gemini_client = AsyncOpenAI(
        api_key=gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=gemini_client,
    )


def create_configured_model(config: ModelConfig):
    """Build the configured model without placing provider choices in application code."""
    if config.provider == "nvidia":
        return create_nvidia_model(config.name)
    if config.provider == "gemini":
        return create_gemini_model(config.name)
    raise ValueError(f"Unsupported model provider: {config.provider}")
