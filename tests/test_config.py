import pytest

from app.config import load_model_config


def test_load_model_config(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[model]\nprovider = "gemini"\nname = "gemini-test"\n', encoding="utf-8")
    assert load_model_config(path).provider == "gemini"


def test_rejects_unknown_provider(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[model]\nprovider = "unknown"\nname = "model"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        load_model_config(path)
