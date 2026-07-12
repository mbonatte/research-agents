"""Constrained local Git and file-editing tools for the thesis writer agent."""

import re
import subprocess
import os
from urllib.parse import urlparse

import requests

from agents import function_tool

from tools.latex import get_repo_root, safe_repo_path
from tools.github import get_git_env


def git(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *command], cwd=get_repo_root(), env=get_git_env(), capture_output=True, text=True, timeout=120)


def current_branch() -> str:
    result = git(["branch", "--show-current"])
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def ensure_safe_branch() -> None:
    if current_branch() in {"main", "master"}:
        raise RuntimeError("Writer changes are forbidden on main/master. Create a writer branch first.")


@function_tool
def create_writer_branch(ticket_id: str, topic: str) -> str:
    """Create and switch to a clean local `agent/<ticket>-<topic>` branch."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40] or "update"
    ticket = re.sub(r"[^a-zA-Z0-9-]+", "-", ticket_id).strip("-") or "ticket"
    branch = f"agent/{ticket.lower()}-{slug}"
    status = git(["status", "--porcelain"])
    if status.returncode:
        return f"Error checking Git status: {status.stderr.strip()}"
    if status.stdout.strip():
        return "Error: Repository has uncommitted changes; refusing to create a writer branch."
    if current_branch() in {"main", "master"}:
        result = git(["switch", "-c", branch])
    else:
        result = git(["switch", "-c", branch])
    if result.returncode:
        return f"Error creating branch: {result.stderr.strip()}"
    return f"Created and switched to {branch}."


@function_tool
def replace_thesis_text(relative_path: str, expected_text: str, replacement_text: str) -> str:
    """Replace exactly one verified text fragment in a `.tex` or `.bib` thesis file.

    Read the file first. The operation fails if the expected text is absent or ambiguous.
    """
    if not relative_path.lower().endswith((".tex", ".bib")):
        return "Error: Writer may edit only .tex or .bib files."
    try:
        ensure_safe_branch()
        path = safe_repo_path(relative_path)
        content = path.read_text(encoding="utf-8")
        count = content.count(expected_text)
        if count != 1:
            return f"Error: expected_text must occur exactly once; found {count} occurrence(s)."
        path.write_text(content.replace(expected_text, replacement_text, 1), encoding="utf-8")
        return f"Updated {relative_path}."
    except Exception as exc:
        return f"Error updating thesis file: {exc}"


@function_tool
def validate_writer_changes() -> str:
    """Run lightweight, non-destructive Git validation for current writer changes."""
    try:
        ensure_safe_branch()
        diff_check = git(["diff", "--check"])
        status = git(["status", "--short"])
        if diff_check.returncode:
            return f"Validation failed:\n{diff_check.stdout}\n{diff_check.stderr}"
        return f"Validation passed (git diff --check).\nChanged files:\n{status.stdout or '(none)'}"
    except Exception as exc:
        return f"Error validating writer changes: {exc}"


@function_tool
def commit_writer_changes(message: str) -> str:
    """Commit intended `.tex` and `.bib` changes on a non-protected local branch."""
    try:
        ensure_safe_branch()
        changed = git(["diff", "--name-only"])
        files = [line for line in changed.stdout.splitlines() if line]
        if not files:
            return "Error: No changes to commit."
        if any(not file.lower().endswith((".tex", ".bib")) for file in files):
            return "Error: Refusing to commit changes outside .tex/.bib files."
        check = git(["diff", "--check"])
        if check.returncode:
            return f"Error: diff validation failed:\n{check.stdout}\n{check.stderr}"
        staged = git(["add", "--", *files])
        if staged.returncode:
            return f"Error staging changes: {staged.stderr.strip()}"
        committed = git(["commit", "-m", message])
        if committed.returncode:
            return f"Error committing changes: {committed.stderr.strip()}"
        return committed.stdout.strip()
    except Exception as exc:
        return f"Error committing writer changes: {exc}"


@function_tool
def push_writer_branch() -> str:
    """Push the current non-protected writer branch to origin."""
    try:
        ensure_safe_branch()
        branch = current_branch()
        result = git(["push", "-u", "origin", branch])
        if result.returncode:
            return f"Error pushing branch: {result.stderr.strip()}"
        return f"Pushed {branch} to origin."
    except Exception as exc:
        return f"Error pushing writer branch: {exc}"


@function_tool
def create_writer_pull_request(title: str, body: str, base_branch: str = "main") -> str:
    """Create a GitHub pull request from the current writer branch. Never merges it."""
    try:
        ensure_safe_branch()
        token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not token:
            return "Error: Missing GITHUB_ACCESS_TOKEN."
        remote = git(["remote", "get-url", "origin"])
        if remote.returncode:
            return f"Error reading origin remote: {remote.stderr.strip()}"
        value = remote.stdout.strip()
        repo = re.sub(r"^git@github\.com:", "", value)
        repo = re.sub(r"^https?://github\.com/", "", repo).removesuffix(".git")
        if not re.fullmatch(r"[^/]+/[^/]+", repo):
            return "Error: origin is not a GitHub owner/repository remote."
        response = requests.post(
            f"https://api.github.com/repos/{repo}/pulls",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"title": title, "head": current_branch(), "base": base_branch, "body": body},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return f"Created pull request #{data.get('number')}: {data.get('html_url')}"
    except requests.RequestException as exc:
        return f"Error creating pull request: {exc}"
    except Exception as exc:
        return f"Error creating pull request: {exc}"
