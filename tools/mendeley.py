"""Pure normalization helpers for Mendeley document payloads."""

from typing import Any


def format_mendeley_authors(authors: list[dict[str, Any]] | None) -> str:
    return "; ".join(
        " ".join(part for part in (author.get("first_name", "").strip(), author.get("last_name", "").strip()) if part)
        for author in (authors or [])
        if author.get("first_name") or author.get("last_name")
    )


def mendeley_document_to_archive_record(
    document: dict[str, Any], files_by_document_id: dict[str, list[dict[str, Any]]] | None = None
) -> dict[str, str]:
    """Normalize a Mendeley document for a schema-aware Notion archive upsert."""
    identifiers = document.get("identifiers") or {}
    document_id = str(document.get("id") or "")
    files = (files_by_document_id or {}).get(document_id, [])
    preferred_file = next((item.get("id") for item in files if item.get("mime_type") == "application/pdf" and item.get("id")), None)
    preferred_file = preferred_file or next((item.get("id") for item in files if item.get("id")), "")
    first = lambda key: (identifiers.get(key) or [""])[0] if isinstance(identifiers.get(key), list) else (identifiers.get(key) or "")
    return {
        "title": str(document.get("title") or ""), "mendeley_id": document_id,
        "authors": format_mendeley_authors(document.get("authors")), "year": str(document.get("year") or ""),
        "venue": str(document.get("source") or ""), "abstract": str(document.get("abstract") or ""),
        "source_type": str(document.get("type") or ""), "doi": str(first("doi")),
        "citation_key": str(document.get("citation_key") or ""), "file_id": str(preferred_file or ""),
        "keywords": "; ".join(document.get("keywords") or []), "tags": "; ".join(document.get("tags") or []),
        "created": str(document.get("created") or ""), "last_modified": str(document.get("last_modified") or ""),
    }
