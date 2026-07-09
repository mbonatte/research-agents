import os
import base64
import subprocess
import tempfile
from pathlib import Path

from agents import function_tool

LOCAL_REPOS_DIR = Path.cwd() / "repositories"
LOCAL_REPO_PATH = LOCAL_REPOS_DIR / "thesis"
SSH_KEY_PATH = Path.cwd() / ".secrets" / "github_phd_thesis_key"

def get_git_env() -> dict:
    """
    Prepare Git environment using the base64-encoded SSH private key.

    Required environment variable:
    - GITHUB_PHD_THESIS_KEY_PRIVATE
    """

    private_key_b64 = os.getenv("GITHUB_PHD_THESIS_KEY_PRIVATE")

    if not private_key_b64:
        raise RuntimeError("Missing GITHUB_PHD_THESIS_KEY_PRIVATE")

    SSH_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)

    key_bytes = base64.b64decode(private_key_b64)
    SSH_KEY_PATH.write_bytes(key_bytes)

    # chmod works on Unix/macOS. On Windows it is mostly harmless.
    try:
        SSH_KEY_PATH.chmod(0o600)
    except Exception:
        pass

    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = (
        f'ssh -i "{SSH_KEY_PATH}" '
        "-o IdentitiesOnly=yes "
        "-o StrictHostKeyChecking=accept-new"
    )

    return env


def run_command(command: list[str], cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """
    Run a shell command safely without shell=True.
    """

    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=get_git_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )

@function_tool
def clone_or_update_thesis_repository() -> str:
    """
    Clone the user's thesis repository into ./repositories/thesis.

    If the repository is already cloned, pull the latest updates.

    Required environment variables:
    - GITHUB_PHD_THESIS_URL
    - GITHUB_PHD_THESIS_KEY_PRIVATE

    Returns the local repository path.
    """

    repo_url = os.getenv("GITHUB_PHD_THESIS_URL")

    if not repo_url:
        return "Error: Missing GITHUB_PHD_THESIS_URL"

    LOCAL_REPOS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if LOCAL_REPO_PATH.exists():
            git_dir = LOCAL_REPO_PATH / ".git"

            if not git_dir.exists():
                return (
                    f"Error: Target path already exists but is not a Git repository: "
                    f"{LOCAL_REPO_PATH}"
                )

            status = run_command(
                ["git", "status", "--porcelain"],
                cwd=LOCAL_REPO_PATH,
            )

            if status.returncode != 0:
                return (
                    "Error checking repository status:\n"
                    f"STDOUT:\n{status.stdout}\n\n"
                    f"STDERR:\n{status.stderr}"
                )

            if status.stdout.strip():
                return (
                    "Repository already exists but has local uncommitted changes. "
                    "I will not run git pull because it may overwrite or conflict with local work.\n\n"
                    f"Repository path: {LOCAL_REPO_PATH}\n\n"
                    f"git status --porcelain:\n{status.stdout}"
                )

            pull = run_command(
                ["git", "pull", "--ff-only"],
                cwd=LOCAL_REPO_PATH,
            )

            if pull.returncode != 0:
                return (
                    "Error pulling repository updates:\n"
                    f"STDOUT:\n{pull.stdout}\n\n"
                    f"STDERR:\n{pull.stderr}"
                )

            return (
                "Repository already cloned. Pulled latest updates successfully.\n"
                f"Repository path: {LOCAL_REPO_PATH}\n\n"
                f"git pull output:\n{pull.stdout}"
            )

        clone = run_command(
            ["git", "clone", repo_url, str(LOCAL_REPO_PATH)],
            cwd=LOCAL_REPOS_DIR,
            timeout=180,
        )

        if clone.returncode != 0:
            return (
                "Error cloning repository:\n"
                f"STDOUT:\n{clone.stdout}\n\n"
                f"STDERR:\n{clone.stderr}"
            )

        return f"Repository cloned successfully to: {LOCAL_REPO_PATH}"

    except Exception as exc:
        return f"Error: {exc}"