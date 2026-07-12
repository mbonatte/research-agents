"""Load non-secret, version-controlled application settings from config.toml."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


CONFIG_PATH = Path.cwd() / "config.toml"
SUPPORTED_PROVIDERS = {"nvidia", "gemini"}


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    name: str


def load_model_config(path: Path = CONFIG_PATH) -> ModelConfig:
    """Load and validate the selected LLM provider and model name."""
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Restore config.toml from version control.")
    with path.open("rb") as config_file:
        data = tomllib.load(config_file)
    model = data.get("model", {})
    provider = str(model.get("provider", "")).strip().lower()
    name = str(model.get("name", "")).strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported model.provider={provider!r}. Choose one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}.")
    if not name:
        raise ValueError("model.name must not be empty in config.toml.")
    return ModelConfig(provider=provider, name=name)
