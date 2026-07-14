"""Agent tool for securely downloading a user-library Mendeley PDF."""

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from agents import function_tool

from tools.mendeley_sync import valid_access_token


FILES_URL = "https://api.mendeley.com/files"
DEFAULT_DOWNLOAD_DIRECTORY = Path(".runs") / "mendeley-pdfs"
MENDELEY_USER_AGENT = "Mozilla/5.0"


def safe_filename(value: str) -> str:
    """Return a Windows-safe filename, keeping agent artifacts in one directory."""
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return value or "mendeley_file.pdf"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_curl(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().replace("\n", " ")[:500]
        raise RuntimeError(f"curl failed: {detail or 'no response detail'}")


def temporary_download_url(file_id: str, token: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".headers", delete=False) as header_file:
        header_path = Path(header_file.name)
    try:
        run_curl([
            "curl.exe", "--silent", "--dump-header", str(header_path), "--output", "NUL",
            "--request", "GET", f"{FILES_URL}/{file_id}",
            "--header", f"Authorization: Bearer {token}",
            "--header", "Accept: application/vnd.mendeley-file.1+json",
            "--user-agent", MENDELEY_USER_AGENT,
        ])
        locations = [
            line.split(":", 1)[1].strip()
            for line in header_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.lower().startswith("location:")
        ]
        if not locations:
            raise RuntimeError("Mendeley did not provide a download redirect for this file.")
        return locations[-1]
    finally:
        header_path.unlink(missing_ok=True)


def fetch_mendeley_pdf(file_id: str, output_directory: Path = DEFAULT_DOWNLOAD_DIRECTORY) -> dict[str, str | int]:
    """Download one Mendeley file via its authenticated temporary redirect URL."""
    file_id = file_id.strip()
    if not file_id:
        raise ValueError("file_id must not be empty")

    token = valid_access_token()
    download_url = temporary_download_url(file_id, token)

    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / safe_filename(f"{file_id}.pdf")
    temporary_path = output_path.with_suffix(".part")
    try:
        run_curl([
            "curl.exe", "--silent", "--show-error", "--fail", "--location",
            "--output", str(temporary_path), download_url,
        ])

        with temporary_path.open("rb") as file:
            if file.read(5) != b"%PDF-":
                raise RuntimeError("Downloaded content is not a PDF; temporary file was removed.")
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return {
        "file_id": file_id,
        "path": str(output_path.resolve()),
        "bytes": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
    }


@function_tool
def download_mendeley_pdf(file_id: str) -> str:
    """Download a Mendeley PDF identified by the File ID stored in Notion.

    Uses the environment's user-authorized Mendeley token, follows the one-time
    download redirect, verifies the PDF signature, and saves the temporary file under
    `.runs/mendeley-pdfs`. Use only for approved sources and do not disclose tokens or
    signed download URLs. Returns the local path, byte size, and SHA-256 checksum.
    """
    try:
        return json.dumps(fetch_mendeley_pdf(file_id), ensure_ascii=False)
    except (OSError, RuntimeError, ValueError) as exc:
        return f"Error: Could not download Mendeley PDF: {exc}"
