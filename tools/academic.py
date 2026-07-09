import httpx
from typing import Optional
from agents import function_tool

# web_search
# fetch_url_metadata


@function_tool
async def search_openalex(
    query: str,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    max_results: int = 10,
) -> list[dict]:
    """
    Search OpenAlex for academic works.

    Use this tool to find candidate scientific articles, books, conference papers,
    reviews, and reports. Returns normalized metadata including title, authors,
    year, DOI, venue, citation count, open access status, abstract when available,
    and OpenAlex URL.

    Args:
        query: Search query, for example "digital twin railway bridge asset management".
        from_year: Optional minimum publication year.
        to_year: Optional maximum publication year.
        max_results: Maximum number of works to return. Use 5-25.

    Returns:
        A list of candidate works with normalized metadata.
    """

    max_results = max(1, min(max_results, 25))

    filters = []

    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")

    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")

    params = {
        "search": query,
        "per-page": max_results,
        "sort": "cited_by_count:desc",
    }

    if filters:
        params["filter"] = ",".join(filters)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.openalex.org/works",
            params=params,
        )
        response.raise_for_status()
        data = response.json()

    results = []

    for work in data.get("results", []):
        authorships = work.get("authorships", [])

        authors = [
            authorship.get("author", {}).get("display_name")
            for authorship in authorships
            if authorship.get("author", {}).get("display_name")
        ]

        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        open_access = work.get("open_access") or {}

        results.append({
            "openalex_id": work.get("id"),
            "title": work.get("title"),
            "authors": authors,
            "year": work.get("publication_year"),
            "publication_date": work.get("publication_date"),
            "doi": work.get("doi"),
            "venue": source.get("display_name"),
            "source_type": work.get("type"),
            "cited_by_count": work.get("cited_by_count"),
            "is_open_access": open_access.get("is_oa"),
            "open_access_url": open_access.get("oa_url"),
            "official_url": primary_location.get("landing_page_url"),
            "pdf_url": primary_location.get("pdf_url"),
            "abstract": reconstruct_openalex_abstract(
                work.get("abstract_inverted_index")
            ),
        })

    return results


def reconstruct_openalex_abstract(abstract_inverted_index: Optional[dict]) -> Optional[str]:
    if not abstract_inverted_index:
        return None

    words_by_position = {}

    for word, positions in abstract_inverted_index.items():
        for position in positions:
            words_by_position[position] = word

    return " ".join(
        words_by_position[position]
        for position in sorted(words_by_position)
    )

@function_tool
async def search_crossref(query: str, max_results: int = 10) -> list[dict]:
    """
    Search Crossref works and return verified publisher metadata.
    """

@function_tool
async def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    """
    
    """

@function_tool
async def search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    """
    
    """

@function_tool
async def get_bibtex_from_doi(doi: str) -> dict:
    """
    Return verified BibTeX for a DOI if available.

    Returns:
    {
        "doi": "...",
        "bibtex": "...",
        "source": "crossref",
        "success": true
    }
    """

