"""Scoped PDF inspection and asset-extraction tools for downloaded Mendeley papers."""

import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any

import fitz
import pdfplumber
from agents import function_tool

from tools.latex import safe_repo_path
from tools.thesis_writer import ensure_safe_branch, git


PDF_DOWNLOAD_DIRECTORY = (Path.cwd() / ".runs" / "mendeley-pdfs").resolve()
PDF_ARTIFACT_DIRECTORY = (Path.cwd() / ".runs" / "pdf-artifacts").resolve()


def safe_pdf_path(pdf_path: str) -> Path:
    """Resolve an existing PDF strictly inside the Mendeley download directory."""
    candidate = Path(pdf_path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    candidate = candidate.resolve()
    if PDF_DOWNLOAD_DIRECTORY not in candidate.parents or candidate.suffix.lower() != ".pdf":
        raise ValueError("pdf_path must refer to a PDF previously downloaded under .runs/mendeley-pdfs.")
    if not candidate.is_file():
        raise FileNotFoundError(f"PDF does not exist: {candidate}")
    return candidate


def artifact_directory(pdf: Path) -> Path:
    path = PDF_ARTIFACT_DIRECTORY / pdf.stem
    path.mkdir(parents=True, exist_ok=True)
    return path


def selected_pages(document: fitz.Document, start_page: int, end_page: int) -> range:
    if start_page < 1:
        raise ValueError("start_page must be at least 1.")
    final_page = end_page or len(document)
    if final_page < start_page or final_page > len(document):
        raise ValueError(f"Choose pages between 1 and {len(document)}.")
    return range(start_page - 1, final_page)


def json_result(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


@function_tool
def inspect_pdf(pdf_path: str) -> str:
    """Inspect a downloaded Mendeley PDF: metadata, page count, dimensions, and outline."""
    try:
        pdf = safe_pdf_path(pdf_path)
        with fitz.open(pdf) as document:
            return json_result({
                "pdf_path": str(pdf),
                "page_count": len(document),
                "metadata": {key: value for key, value in document.metadata.items() if value},
                "first_page_size_points": {"width": document[0].rect.width, "height": document[0].rect.height} if document else {},
                "outline": [{"level": level, "title": title, "page": page} for level, title, page in document.get_toc()[:100]],
            })
    except Exception as exc:
        return f"Error inspecting PDF: {exc}"


@function_tool
def extract_pdf_text(pdf_path: str, start_page: int = 1, end_page: int = 0, max_chars: int = 30000) -> str:
    """Extract text from a page range of a downloaded PDF, preserving page markers for evidence."""
    try:
        pdf = safe_pdf_path(pdf_path)
        with fitz.open(pdf) as document:
            pages = selected_pages(document, start_page, end_page)
            extracted = "\n\n".join(f"[Page {page + 1}]\n{document[page].get_text('text').strip()}" for page in pages)
        if len(extracted) > max(1, max_chars):
            extracted = extracted[:max_chars] + "\n\n[Text truncated.]"
        return extracted or "No selectable text was found in the requested pages."
    except Exception as exc:
        return f"Error extracting PDF text: {exc}"


@function_tool
def search_pdf_text(pdf_path: str, query: str, max_matches: int = 30) -> str:
    """Search a downloaded PDF's selectable text and return page-numbered context snippets."""
    try:
        if not query.strip():
            return "Error searching PDF text: query must not be empty."
        pdf = safe_pdf_path(pdf_path)
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        matches = []
        with fitz.open(pdf) as document:
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text").replace("\n", " ")
                for match in pattern.finditer(text):
                    matches.append({"page": page_number, "context": text[max(0, match.start() - 180):match.end() + 180].strip()})
                    if len(matches) >= max(1, max_matches):
                        return json_result({"query": query, "matches": matches, "truncated": True})
        return json_result({"query": query, "matches": matches, "truncated": False})
    except Exception as exc:
        return f"Error searching PDF text: {exc}"


@function_tool
def extract_pdf_tables(pdf_path: str, start_page: int = 1, end_page: int = 0) -> str:
    """Extract detected tables to CSV files, returning their page numbers and structured rows."""
    try:
        pdf = safe_pdf_path(pdf_path)
        with fitz.open(pdf) as document:
            pages = list(selected_pages(document, start_page, end_page))
        output_dir = artifact_directory(pdf) / "tables"
        output_dir.mkdir(parents=True, exist_ok=True)
        tables = []
        with pdfplumber.open(pdf) as document:
            for page_index in pages:
                for table_index, table in enumerate(document.pages[page_index].extract_tables(), start=1):
                    rows = [[cell or "" for cell in row] for row in table if row]
                    if not rows:
                        continue
                    csv_path = output_dir / f"page-{page_index + 1}-table-{table_index}.csv"
                    with csv_path.open("w", newline="", encoding="utf-8") as file:
                        csv.writer(file).writerows(rows)
                    tables.append({"page": page_index + 1, "path": str(csv_path), "rows": rows})
        return json_result({"pdf_path": str(pdf), "tables": tables})
    except Exception as exc:
        return f"Error extracting PDF tables: {exc}"


@function_tool
def extract_pdf_images(pdf_path: str, start_page: int = 1, end_page: int = 0) -> str:
    """Extract embedded raster images from PDF pages into `.runs/pdf-artifacts` for later LaTeX use."""
    try:
        pdf = safe_pdf_path(pdf_path)
        output_dir = artifact_directory(pdf) / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        extracted, seen_xrefs = [], set()
        with fitz.open(pdf) as document:
            for page_index in selected_pages(document, start_page, end_page):
                for image_index, image in enumerate(document[page_index].get_images(full=True), start=1):
                    xref = image[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    image_data = document.extract_image(xref)
                    extension = image_data.get("ext", "png")
                    image_path = output_dir / f"page-{page_index + 1}-image-{image_index}.{extension}"
                    image_path.write_bytes(image_data["image"])
                    extracted.append({
                        "page": page_index + 1, "path": str(image_path), "width": image_data.get("width"),
                        "height": image_data.get("height"), "colorspace": image_data.get("colorspace"),
                    })
        return json_result({"pdf_path": str(pdf), "images": extracted})
    except Exception as exc:
        return f"Error extracting PDF images: {exc}"


@function_tool
def render_pdf_pages(pdf_path: str, start_page: int = 1, end_page: int = 0, dpi: int = 150) -> str:
    """Render pages to PNGs, including vector figures and tables that are not embedded images."""
    try:
        if not 72 <= dpi <= 300:
            return "Error rendering PDF pages: dpi must be between 72 and 300."
        pdf = safe_pdf_path(pdf_path)
        output_dir = artifact_directory(pdf) / "rendered-pages"
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered = []
        with fitz.open(pdf) as document:
            for page_index in selected_pages(document, start_page, end_page):
                path = output_dir / f"page-{page_index + 1}.png"
                pixmap = document[page_index].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
                pixmap.save(path)
                rendered.append({"page": page_index + 1, "path": str(path), "width": pixmap.width, "height": pixmap.height})
        return json_result({"pdf_path": str(pdf), "dpi": dpi, "pages": rendered})
    except Exception as exc:
        return f"Error rendering PDF pages: {exc}"


@function_tool
def copy_pdf_asset_to_thesis(asset_path: str, destination_relative_path: str) -> str:
    """Copy an extracted PDF image or rendered page into the thesis repository on a safe branch.

    Use a repository-relative `.png`, `.jpg`, `.jpeg`, or `.webp` destination, normally
    below the thesis figure directory. The writer must cite and caption the asset in LaTeX.
    """
    try:
        ensure_safe_branch()
        source = Path(asset_path).resolve()
        if PDF_ARTIFACT_DIRECTORY not in source.parents or source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return "Error copying PDF asset: asset_path must be an extracted or rendered raster artifact."
        if not source.is_file():
            return "Error copying PDF asset: source artifact does not exist."
        destination = safe_repo_path(destination_relative_path)
        if destination.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return "Error copying PDF asset: destination must be a raster image file."
        if destination.exists():
            return "Error copying PDF asset: destination already exists; choose a new filename."
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        staged = git(["add", "--", destination_relative_path])
        if staged.returncode:
            destination.unlink(missing_ok=True)
            return f"Error copying PDF asset: could not stage destination: {staged.stderr.strip()}"
        return json_result({"status": "copied", "destination": destination_relative_path})
    except Exception as exc:
        return f"Error copying PDF asset: {exc}"
