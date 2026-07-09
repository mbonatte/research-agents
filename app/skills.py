from pathlib import Path


def load_skill(path: str) -> str:
    skill_path = Path(path)

    if not skill_path.exists():
        raise FileNotFoundError(
            f"Missing skill file: {skill_path}\n"
            f"Create this file or remove the corresponding agent from the registry."
        )

    return skill_path.read_text(encoding="utf-8")