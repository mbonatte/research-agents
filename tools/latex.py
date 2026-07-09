import os

from pathlib import Path

from agents import function_tool

LOCAL_REPOS_DIR = Path.cwd() / "repositories"
LOCAL_REPO_PATH = LOCAL_REPOS_DIR / "thesis"


def get_repo_root() -> Path:
    """
    Return the local thesis repository root.

    The repository is expected at ./repositories/thesis.
    """

    root = LOCAL_REPO_PATH.resolve()

    if not root.exists():
        raise RuntimeError(
            f"Thesis repository does not exist yet: {root}. "
            "Run clone_or_update_thesis_repository first."
        )

    if not root.is_dir():
        raise RuntimeError(f"Thesis repository path is not a directory: {root}")

    if not (root / ".git").exists():
        raise RuntimeError(f"Path exists but is not a Git repository: {root}")

    return root


def safe_repo_path(relative_path: str) -> Path:
    """
    Resolve a path safely inside the thesis repository.

    Prevents absolute paths and path traversal such as ../../.env.
    """

    root = get_repo_root()

    if Path(relative_path).is_absolute():
        raise ValueError("Use a relative path only, not an absolute path.")

    candidate = (root / relative_path).resolve()

    if root not in candidate.parents and candidate != root:
        raise ValueError(f"Path is outside repository: {relative_path}")

    return candidate


@function_tool
def list_repo_files(max_files: int = 300) -> str:
    """
    List relevant files in the thesis repository.

    Use this to understand repository structure before reading files.
    """

    root = get_repo_root()

    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        ".idea",
        ".vscode",
    }

    ignored_suffixes = {
        ".aux",
        ".bbl",
        ".bcf",
        ".blg",
        ".fdb_latexmk",
        ".fls",
        ".lof",
        ".log",
        ".lot",
        ".out",
        ".run.xml",
        ".synctex.gz",
        ".toc",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".zip",
    }

    files = []

    for path in root.rglob("*"):
        if path.is_dir():
            continue

        relative = path.relative_to(root)

        if any(part in ignored_dirs for part in relative.parts):
            continue

        if any(str(relative).endswith(suffix) for suffix in ignored_suffixes):
            continue

        files.append(str(relative).replace("\\", "/"))

        if len(files) >= max_files:
            break

    return "\n".join(files)


def _read_repo_file_impl(relative_path: str, max_chars: int = 20000) -> str:
    """
    Read a text file from the thesis repository.

    Use relative paths only. Do not use absolute paths.
    """

    try:
        path = safe_repo_path(relative_path)

        if not path.exists():
            return f"Error: File does not exist: {relative_path}"

        if not path.is_file():
            return f"Error: Path is not a file: {relative_path}"

        text = path.read_text(encoding="utf-8", errors="replace")

        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[File truncated because it is long.]"

        return f"FILE: {relative_path}\n\n{text}"

    except Exception as exc:
        return f"Error reading file {relative_path}: {exc}"

@function_tool
def read_repo_file(relative_path: str, max_chars: int = 20000) -> str:
    """
    Read a text file from the thesis repository.

    Use relative paths only. Do not use absolute paths.
    """
    return _read_repo_file_impl(relative_path, max_chars)

@function_tool
def read_repo_files(relative_paths: list[str], max_chars_per_file: int = 20000) -> dict:
    """
    Read multiple repository files in one tool call.

    Use this when several known files need to be inspected together, such as all thesis chapters.

    Args:
        relative_paths: List of repository-relative file paths.
        max_chars_per_file: Maximum characters to return per file.

    Returns:
        A dictionary keyed by file path, with file contents or an error message.
    """

    results = {}

    for relative_path in relative_paths:
        try:
            # Reuse your existing internal file-reading logic here.
            # If read_repo_file is only a decorated tool, extract the real
            # implementation into a helper function and call that helper here.
            content = _read_repo_file_impl(
                relative_path=relative_path,
                max_chars=max_chars_per_file,
            )

            results[relative_path] = {
                "ok": True,
                "content": content,
            }

        except Exception as e:
            results[relative_path] = {
                "ok": False,
                "error": str(e),
            }

    return results

@function_tool
def search_repo_text(query: str, max_matches: int = 50) -> str:
    """
    Search for text inside repository files.

    Use this to find LaTeX commands, sections, citations, labels, TODOs, or bibliography entries.
    """

    root = get_repo_root()

    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
    }

    allowed_suffixes = {
        ".tex",
        ".bib",
        # ".cls",
        # ".sty",
        # ".md",
        # ".txt",
        # ".yml",
        # ".yaml",
        # ".toml",
        # ".json",
    }

    matches = []

    query_lower = query.lower()

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if any(part in ignored_dirs for part in relative.parts):
            continue

        if path.suffix.lower() not in allowed_suffixes:
            continue

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for line_number, line in enumerate(lines, start=1):
            if query_lower in line.lower():
                matches.append(
                    f"{str(relative).replace('\\', '/')}:{line_number}: {line.strip()}"
                )

                if len(matches) >= max_matches:
                    return "\n".join(matches)

    if not matches:
        return f"No matches found for query: {query}"

    return "\n".join(matches)