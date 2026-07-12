"""Read-only academic discovery and metadata-verification tools."""

import re
from typing import Any, Optional
from urllib.parse import quote
from xml.etree import ElementTree

import httpx
from agents import function_tool


def reconstruct_openalex_abstract(abstract_inverted_index: Optional[dict]) -> Optional[str]:
    if not abstract_inverted_index:
        return None
    words_by_position = {position: word for word, positions in abstract_inverted_index.items() for position in positions}
    return " ".join(words_by_position[position] for position in sorted(words_by_position))


def normalize_doi_value(doi: str) -> str:
    """Return a canonical DOI without resolver URLs or a leading `doi:` label."""
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi.strip(), flags=re.I)
    return re.sub(r"^doi:\s*", "", value, flags=re.I).rstrip(" .;,)")


def openalex_result(work: dict[str, Any]) -> dict[str, Any]:
    authors = [item.get("author", {}).get("display_name") for item in work.get("authorships", []) if item.get("author", {}).get("display_name")]
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    open_access = work.get("open_access") or {}
    return {"openalex_id": work.get("id"), "title": work.get("title"), "authors": authors, "year": work.get("publication_year"), "publication_date": work.get("publication_date"), "doi": normalize_doi_value(work["doi"]) if work.get("doi") else None, "venue": source.get("display_name"), "source_type": work.get("type"), "cited_by_count": work.get("cited_by_count"), "is_open_access": open_access.get("is_oa"), "open_access_url": open_access.get("oa_url"), "official_url": primary_location.get("landing_page_url"), "pdf_url": primary_location.get("pdf_url"), "abstract": reconstruct_openalex_abstract(work.get("abstract_inverted_index"))}


@function_tool
async def search_openalex(query: str, from_year: Optional[int] = None, to_year: Optional[int] = None, max_results: int = 10) -> list[dict[str, Any]]:
    """Search OpenAlex for scholarly works with abstracts, citation counts, and OA links."""
    filters = []
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    params: dict[str, Any] = {"search": query, "per-page": max(1, min(max_results, 25)), "sort": "cited_by_count:desc"}
    if filters:
        params["filter"] = ",".join(filters)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://api.openalex.org/works", params=params)
        response.raise_for_status()
    return [openalex_result(work) for work in response.json().get("results", [])]


@function_tool
async def get_openalex_work(openalex_id_or_doi: str) -> dict[str, Any]:
    """Retrieve one OpenAlex work by its OpenAlex ID or DOI to verify candidate metadata."""
    identifier = openalex_id_or_doi.strip()
    if identifier.lower().startswith("10.") or "doi.org" in identifier.lower():
        identifier = f"https://doi.org/{normalize_doi_value(identifier)}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"https://api.openalex.org/works/{quote(identifier, safe=':/')}")
        response.raise_for_status()
    return openalex_result(response.json())


def crossref_result(item: dict[str, Any]) -> dict[str, Any]:
    authors = [" ".join(part for part in (person.get("given"), person.get("family")) if part) for person in item.get("author", [])]
    issued = item.get("issued", {}).get("date-parts", [[None]])[0]
    return {"title": (item.get("title") or [None])[0], "authors": authors, "year": issued[0] if issued else None, "venue": (item.get("container-title") or [None])[0], "publisher": item.get("publisher"), "source_type": item.get("type"), "doi": item.get("DOI"), "official_url": item.get("URL"), "abstract": item.get("abstract"), "citation_count": item.get("is-referenced-by-count"), "references_count": item.get("references-count")}


@function_tool
async def search_crossref(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search Crossref for publisher-registered works; use it to verify DOI metadata."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://api.crossref.org/works", params={"query.bibliographic": query, "rows": max(1, min(max_results, 25))})
        response.raise_for_status()
    return [crossref_result(item) for item in response.json()["message"].get("items", [])]


@function_tool
async def get_crossref_work(doi: str) -> dict[str, Any]:
    """Retrieve verified Crossref metadata for a DOI."""
    canonical_doi = normalize_doi_value(doi)
    if not canonical_doi.startswith("10."):
        return {"error": "A DOI must begin with '10.'."}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"https://api.crossref.org/works/{quote(canonical_doi, safe='')}")
        response.raise_for_status()
    return crossref_result(response.json()["message"])


@function_tool
async def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search Semantic Scholar for citation signals and abstracts. Public API limits apply."""
    fields = "title,authors,year,venue,abstract,externalIds,citationCount,openAccessPdf,url,publicationTypes"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://api.semanticscholar.org/graph/v1/paper/search", params={"query": query, "limit": max(1, min(max_results, 25)), "fields": fields})
        response.raise_for_status()
    return [{"semantic_scholar_id": item.get("paperId"), "title": item.get("title"), "authors": [author.get("name") for author in item.get("authors", [])], "year": item.get("year"), "venue": item.get("venue"), "abstract": item.get("abstract"), "doi": (item.get("externalIds") or {}).get("DOI"), "citation_count": item.get("citationCount"), "official_url": item.get("url"), "pdf_url": (item.get("openAccessPdf") or {}).get("url"), "source_type": item.get("publicationTypes")} for item in response.json().get("data", [])]


@function_tool
async def search_arxiv(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search arXiv for clearly labelled preprints and their abstracts/PDF URLs."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://export.arxiv.org/api/query", params={"search_query": f"all:{query}", "start": 0, "max_results": max(1, min(max_results, 25))})
        response.raise_for_status()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ElementTree.fromstring(response.text)
    results = []
    for entry in root.findall("atom:entry", ns):
        links = {link.get("title") or link.get("rel"): link.get("href") for link in entry.findall("atom:link", ns)}
        results.append({"arxiv_id": entry.findtext("atom:id", default="", namespaces=ns).rsplit("/", 1)[-1], "title": " ".join(entry.findtext("atom:title", default="", namespaces=ns).split()), "authors": [author.findtext("atom:name", default="", namespaces=ns) for author in entry.findall("atom:author", ns)], "published": entry.findtext("atom:published", default="", namespaces=ns), "abstract": " ".join(entry.findtext("atom:summary", default="", namespaces=ns).split()), "official_url": links.get("alternate"), "pdf_url": links.get("pdf"), "source_type": "preprint"})
    return results


@function_tool
async def get_bibtex_from_doi(doi: str) -> dict[str, Any]:
    """Fetch DOI content negotiation BibTeX. Do not use it as metadata verification by itself."""
    canonical_doi = normalize_doi_value(doi)
    if not canonical_doi.startswith("10."):
        return {"success": False, "doi": canonical_doi, "error": "A DOI must begin with '10.'."}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"https://doi.org/{quote(canonical_doi, safe='/')}", headers={"Accept": "application/x-bibtex"}, follow_redirects=True)
        response.raise_for_status()
    return {"success": True, "doi": canonical_doi, "bibtex": response.text, "source": "DOI content negotiation"}
