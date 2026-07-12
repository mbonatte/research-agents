import os
import requests
import json
from typing import Any

from agents import function_tool

NOTION_VERSION = "2022-06-28"
RICH_TEXT_CHUNK_SIZE = 2_000
TITLE_CHUNK_SIZE = 100


def notion_headers() -> dict[str, str]:
    notion_token = os.getenv("NOTION_API_KEY_PHD_THESIS")

    if not notion_token:
        raise RuntimeError("Missing NOTION_API_KEY_PHD_THESIS in .env")

    return {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def rich_text_to_plain_text(value: dict[str, Any]) -> str:
    items = value.get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in items).strip()


def title_to_plain_text(value: dict[str, Any]) -> str:
    items = value.get("title", [])
    return "".join(item.get("plain_text", "") for item in items).strip()


def select_to_plain_text(value: dict[str, Any]) -> str:
    selected = value.get("select")
    if not selected:
        return ""
    return selected.get("name", "")


def extract_ticket_from_page(page: dict[str, Any]) -> dict[str, str]:
    props = page.get("properties", {})

    return {
        "ticket_id": title_to_plain_text(props.get("ticket_id", {})),
        "severity": select_to_plain_text(props.get("severity", {})),
        "issue_type": select_to_plain_text(props.get("issue_type", {})),
        "confidence": select_to_plain_text(props.get("confidence", {})),
        "location": rich_text_to_plain_text(props.get("location", {})),
        "diagnosis": rich_text_to_plain_text(props.get("diagnosis", {})),
        "evidence": rich_text_to_plain_text(props.get("evidence", {})),
        "why_it_matters": rich_text_to_plain_text(props.get("why_it_matters", {})),
        "suggested_research_directions": rich_text_to_plain_text(
            props.get("suggested_research_directions", {})
        ),
        "expected_improvement": rich_text_to_plain_text(
            props.get("expected_improvement", {})
        ),
    }


def text_blocks(value: str, chunk_size: int = RICH_TEXT_CHUNK_SIZE) -> list[dict[str, Any]]:
    """Convert text to Notion rich-text blocks without exceeding its per-block limit."""
    if not value:
        return []

    return [
        {
            "type": "text",
            "text": {"content": value[start : start + chunk_size]},
        }
        for start in range(0, len(value), chunk_size)
    ]


def find_ticket_pages(ticket_id: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    """Return database pages whose title property exactly matches ``ticket_id``."""
    database_id = os.getenv("NOTION_DATABASE_TICKET_ID")
    if not database_id:
        raise RuntimeError("Missing NOTION_DATABASE_TICKET_ID in .env")

    response = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=headers,
        json={
            "filter": {"property": "ticket_id", "title": {"equals": ticket_id}},
            "page_size": 10,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def notion_property_text(value: dict[str, Any]) -> str:
    """Extract the display text from the common Notion database property types."""
    property_type = value.get("type")
    if property_type in {"title", "rich_text"}:
        return "".join(item.get("plain_text", "") for item in value.get(property_type, []))
    if property_type in {"url", "email", "phone_number"}:
        return value.get(property_type) or ""
    if property_type in {"select", "status"}:
        selected = value.get(property_type)
        return selected.get("name", "") if selected else ""
    return ""


def find_schema_property(schema: dict[str, Any], names: tuple[str, ...]) -> tuple[str, dict[str, Any]] | None:
    """Find a Notion property by a case-insensitive canonical field name."""
    normalize = lambda value: " ".join(value.lower().replace("_", " ").replace("-", " ").split())
    normalized_names = {normalize(name) for name in names}
    for name, definition in schema.items():
        normalized = normalize(name)
        if normalized in normalized_names:
            return name, definition
    return None


def first_title_property(schema: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for name, definition in schema.items():
        if definition.get("type") == "title":
            return name, definition
    return None


def notion_text_property(property_type: str, value: str) -> dict[str, Any] | None:
    if not value:
        return None
    if property_type == "title":
        return {"title": text_blocks(value, TITLE_CHUNK_SIZE)}
    if property_type == "rich_text":
        return {"rich_text": text_blocks(value)}
    if property_type == "url":
        return {"url": value}
    if property_type == "number":
        try:
            return {"number": int(value)}
        except ValueError:
            return None
    return None


def source_search_filter(name: str, definition: dict[str, Any], value: str) -> dict[str, Any] | None:
    property_type = definition.get("type")
    if property_type == "title":
        return {"property": name, "title": {"equals": value[:100]}}
    if property_type == "rich_text":
        return {"property": name, "rich_text": {"contains": value[:100]}}
    if property_type == "url":
        return {"property": name, "url": {"equals": value}}
    return None


def database_schema(database_id: str, headers: dict[str, str]) -> dict[str, Any]:
    response = requests.get(
        f"https://api.notion.com/v1/databases/{database_id}", headers=headers, timeout=20
    )
    response.raise_for_status()
    return response.json().get("properties", {})


def add_missing_properties(
    database_id: str, headers: dict[str, str], properties: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Add only absent properties, preserving all existing database configuration."""
    schema = database_schema(database_id, headers)
    missing = {name: definition for name, definition in properties.items() if name not in schema}
    if not missing:
        return schema
    response = requests.patch(
        f"https://api.notion.com/v1/databases/{database_id}",
        headers=headers,
        json={"properties": missing},
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("properties", schema)


def fit_review_properties() -> dict[str, dict[str, Any]]:
    return {
        "Fit Decision": {"select": {}},
        "Reviewer Evidence Access": {"select": {}},
        "Agent 4 Citation Use": {"select": {}},
        "Fit Reviewed At": {"date": {}},
        "Fit Review Summary": {"rich_text": {}},
        "Claim Support": {"rich_text": {}},
        "Do Not Use For": {"rich_text": {}},
        "Literature Fit Scores JSON": {"rich_text": {}},
        "Recommended Agent 4 Action": {"rich_text": {}},
        "Bibliography Review": {"rich_text": {}},
        "Conflict/Tension": {"rich_text": {}},
        "Target Thesis Location": {"rich_text": {}},
    }


def fit_review_page_properties(
    *,
    fit_decision: str,
    evidence_access: str,
    citation_use: str,
    summary: str,
    claim_support: str,
    do_not_use_for: str,
    scores_json: str,
    recommended_action: str,
    bibliography_review: str,
    conflict_tension: str,
    target_thesis_location: str,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    values = {
        "Fit Decision": {"select": {"name": fit_decision}},
        "Reviewer Evidence Access": {"select": {"name": evidence_access}},
        "Agent 4 Citation Use": {"select": {"name": citation_use}},
        "Fit Reviewed At": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
        "Fit Review Summary": {"rich_text": text_blocks(summary)},
        "Claim Support": {"rich_text": text_blocks(claim_support)},
        "Do Not Use For": {"rich_text": text_blocks(do_not_use_for)},
        "Literature Fit Scores JSON": {"rich_text": text_blocks(scores_json)},
        "Recommended Agent 4 Action": {"rich_text": text_blocks(recommended_action)},
        "Bibliography Review": {"rich_text": text_blocks(bibliography_review)},
        "Conflict/Tension": {"rich_text": text_blocks(conflict_tension)},
        "Target Thesis Location": {"rich_text": text_blocks(target_thesis_location)},
    }
    return {name: value for name, value in values.items() if value}


def update_mendeley_article(
    *,
    title: str,
    mendeley_id: str = "",
    doi: str = "",
    authors: str = "",
    year: str = "",
    venue: str = "",
    abstract: str = "",
    official_url: str = "",
    source_type: str = "",
    page_id: str = "",
) -> dict[str, Any]:
    """Create or update one Notion/Mendeley archive record.

    This is an application helper, intentionally not an ``@function_tool``. If no
    ``page_id`` is supplied, it finds an existing record using Mendeley ID, DOI, then
    title. Multiple matches raise an error rather than risking the wrong update.
    Only properties that exist in the current Notion schema are populated.
    """
    title = title.strip()
    if not title:
        raise ValueError("title must not be empty")

    database_id = os.getenv("NOTION_DATABASE_MENDELEY_ID")
    if not database_id:
        raise RuntimeError("Missing NOTION_DATABASE_MENDELEY_ID in .env")
    headers = notion_headers()

    try:
        schema_response = requests.get(
            f"https://api.notion.com/v1/databases/{database_id}", headers=headers, timeout=20
        )
        schema_response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not inspect the Mendeley database: {exc}") from exc
    schema = schema_response.json().get("properties", {})
    title_property = find_schema_property(schema, ("title", "paper title", "article title", "name")) or first_title_property(schema)
    if not title_property:
        raise RuntimeError("The Mendeley database has no title property")

    aliases = {
        "mendeley_id": ("mendeley id", "mendeley_id", "document id", "document_id"),
        "doi": ("doi",),
        "authors": ("authors", "author"),
        "year": ("year", "publication year"),
        "venue": ("venue", "journal", "publication", "container title"),
        "abstract": ("abstract", "summary"),
        "official_url": ("official url", "url", "link", "source url"),
        "source_type": ("source type", "type", "publication type"),
    }
    matched_page_id = page_id.strip()
    if not matched_page_id:
        candidates = [
            (aliases["mendeley_id"], mendeley_id),
            (aliases["doi"], doi),
            (("title", "paper title", "article title", "name"), title),
        ]
        for property_names, value in candidates:
            if not value:
                continue
            match = find_schema_property(schema, property_names)
            if not match:
                continue
            filter_payload = source_search_filter(match[0], match[1], value)
            if not filter_payload:
                continue
            try:
                response = requests.post(
                    f"https://api.notion.com/v1/databases/{database_id}/query",
                    headers=headers,
                    json={"filter": filter_payload, "page_size": 2},
                    timeout=20,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(f"Could not query the Mendeley database: {exc}") from exc
            pages = response.json().get("results", [])
            if len(pages) > 1:
                raise RuntimeError("Multiple Mendeley records match; pass page_id to update safely")
            if pages:
                matched_page_id = pages[0].get("id", "")
                break

    values = {
        "title": title,
        "mendeley_id": mendeley_id,
        "doi": doi,
        "authors": authors,
        "year": year,
        "venue": venue,
        "abstract": abstract,
        "official_url": official_url,
        "source_type": source_type,
    }
    properties: dict[str, Any] = {}
    for field, value in values.items():
        match = title_property if field == "title" else find_schema_property(schema, aliases[field])
        if not match:
            continue
        property_value = notion_text_property(match[1].get("type", ""), value)
        if property_value:
            properties[match[0]] = property_value

    try:
        if matched_page_id:
            response = requests.patch(
                f"https://api.notion.com/v1/pages/{matched_page_id}",
                headers=headers,
                json={"properties": properties},
                timeout=20,
            )
            status = "updated"
        else:
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json={"parent": {"database_id": database_id}, "properties": properties},
                timeout=20,
            )
            status = "created"
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not {status} the Mendeley record: {exc}") from exc

    page = response.json()
    return {
        "status": status,
        "page_id": page.get("id"),
        "url": page.get("url"),
        "populated_properties": list(properties),
    }


@function_tool
def list_search_articles(ticket_id: str = "", max_results: int = 100) -> str:
    """Read candidate articles from the Notion Search database for fit review.

    When a ticket ID is provided, returned records are filtered locally using any
    recognized Ticket ID property. This tool is read-only.
    """
    database_id = os.getenv("NOTION_DATABASE_SEARCH_ID")
    if not database_id:
        return "Error: Missing NOTION_DATABASE_SEARCH_ID in .env"
    try:
        headers = notion_headers()
        schema = database_schema(database_id, headers)
        response = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json={"page_size": max(1, min(max_results, 100))},
            timeout=20,
        )
        response.raise_for_status()
    except (RuntimeError, requests.RequestException) as exc:
        return f"Error: Could not read literature-search records: {exc}"

    title_property = first_title_property(schema)
    ticket_property = find_schema_property(schema, ("ticket id", "ticket_id", "ticket"))
    records = []
    for page in response.json().get("results", []):
        props = page.get("properties", {})
        found_ticket_id = notion_property_text(props.get(ticket_property[0], {})) if ticket_property else ""
        if ticket_id and ticket_id.lower() not in found_ticket_id.lower():
            continue
        records.append({
            "page_id": page.get("id"),
            "url": page.get("url"),
            "title": notion_property_text(props.get(title_property[0], {})) if title_property else "",
            "ticket_id": found_ticket_id,
            "properties": {name: notion_property_text(value) for name, value in props.items() if notion_property_text(value)},
        })
    return json.dumps(records, ensure_ascii=False)


@function_tool
def write_literature_fit_review(
    page_id: str,
    fit_decision: str,
    evidence_access: str,
    citation_use: str,
    summary: str,
    claim_support: str = "",
    do_not_use_for: str = "",
    scores_json: str = "",
    recommended_action: str = "",
    bibliography_review: str = "",
    conflict_tension: str = "",
    target_thesis_location: str = "",
) -> str:
    """Write a completed fit review to a candidate article in the Search database.

    Call this only when the user asks for Notion writeback. Missing review properties
    are added without changing unrelated fields.
    """
    allowed = {"strong_accept", "accept", "background_only", "uncertain", "reject"}
    if fit_decision not in allowed:
        return f"Error: fit_decision must be one of {', '.join(sorted(allowed))}."
    database_id = os.getenv("NOTION_DATABASE_SEARCH_ID")
    if not database_id:
        return "Error: Missing NOTION_DATABASE_SEARCH_ID in .env"
    try:
        headers = notion_headers()
        add_missing_properties(database_id, headers, fit_review_properties())
        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            json={"properties": fit_review_page_properties(
                fit_decision=fit_decision, evidence_access=evidence_access,
                citation_use=citation_use, summary=summary, claim_support=claim_support,
                do_not_use_for=do_not_use_for, scores_json=scores_json,
                recommended_action=recommended_action, bibliography_review=bibliography_review,
                conflict_tension=conflict_tension, target_thesis_location=target_thesis_location,
            )},
            timeout=20,
        )
        response.raise_for_status()
    except (RuntimeError, requests.RequestException) as exc:
        return f"Error: Could not write literature fit review: {exc}"
    page = response.json()
    return json.dumps({"status": "updated", "page_id": page.get("id"), "url": page.get("url")}, ensure_ascii=False)


@function_tool
def write_ticket_literature_fit_summary(
    ticket_id: str, summary: str, recommended_source_set: str, status: str = "complete"
) -> str:
    """Write the fit-review summary and recommended sources back to a thesis ticket."""
    database_id = os.getenv("NOTION_DATABASE_TICKET_ID")
    if not database_id:
        return "Error: Missing NOTION_DATABASE_TICKET_ID in .env"
    try:
        headers = notion_headers()
        pages = find_ticket_pages(ticket_id, headers)
        if not pages:
            return f"Error: No ticket found with ticket_id={ticket_id!r}."
        if len(pages) > 1:
            return f"Error: Multiple tickets found with ticket_id={ticket_id!r}."
        add_missing_properties(database_id, headers, {
            "Literature Fit Review Status": {"rich_text": {}},
            "Literature Fit Review Summary": {"rich_text": {}},
            "Recommended Source Set": {"rich_text": {}},
        })
        response = requests.patch(
            f"https://api.notion.com/v1/pages/{pages[0].get('id')}",
            headers=headers,
            json={"properties": {
                "Literature Fit Review Status": {"rich_text": text_blocks(status)},
                "Literature Fit Review Summary": {"rich_text": text_blocks(summary)},
                "Recommended Source Set": {"rich_text": text_blocks(recommended_source_set)},
            }},
            timeout=20,
        )
        response.raise_for_status()
    except (RuntimeError, requests.RequestException) as exc:
        return f"Error: Could not write ticket fit-review summary: {exc}"
    page = response.json()
    return json.dumps({"status": "updated", "ticket_id": ticket_id, "page_id": page.get("id")}, ensure_ascii=False)


@function_tool
def check_mendeley_archive(title: str, doi: str = "") -> str:
    """Check the Notion/Mendeley archive for an existing source by DOI and title.

    Use this for every source retained from a literature search. It only reads the
    configured Mendeley database and returns matching archive records; it never edits
    the archive.
    """
    database_id = os.getenv("NOTION_DATABASE_MENDELEY_ID")
    if not database_id:
        return "Error: Missing NOTION_DATABASE_MENDELEY_ID in .env"

    title = title.strip()
    canonical_doi = doi.lower().replace("https://doi.org/", "").replace("doi:", "").strip()
    if not title and not canonical_doi:
        return "Error: Provide a title or DOI to check the Mendeley archive."

    try:
        headers = notion_headers()
        schema_response = requests.get(
            f"https://api.notion.com/v1/databases/{database_id}", headers=headers, timeout=20
        )
        schema_response.raise_for_status()
        schema = schema_response.json().get("properties", {})
    except (RuntimeError, requests.RequestException) as exc:
        return f"Error: Could not inspect the Mendeley database: {exc}"

    doi_property = find_schema_property(schema, ("doi",))
    title_property = find_schema_property(schema, ("title", "paper title", "article title", "name"))
    if not doi_property and not title_property:
        return "Error: The Mendeley database has no recognized DOI or title property."

    filters = []
    if canonical_doi and doi_property:
        name, definition = doi_property
        property_type = definition.get("type")
        if property_type == "rich_text":
            filters.append({"property": name, "rich_text": {"contains": canonical_doi}})
        elif property_type == "title":
            filters.append({"property": name, "title": {"contains": canonical_doi}})
        elif property_type == "url":
            filters.append({"property": name, "url": {"equals": canonical_doi}})
    if title and title_property:
        name, definition = title_property
        property_type = definition.get("type")
        query_title = title[:100]
        if property_type == "title":
            filters.append({"property": name, "title": {"contains": query_title}})
        elif property_type == "rich_text":
            filters.append({"property": name, "rich_text": {"contains": query_title}})

    matches_by_id: dict[str, dict[str, Any]] = {}
    for filter_payload in filters:
        try:
            response = requests.post(
                f"https://api.notion.com/v1/databases/{database_id}/query",
                headers=headers,
                json={"filter": filter_payload, "page_size": 20},
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return f"Error: Could not query the Mendeley database: {exc}"
        for page in response.json().get("results", []):
            properties = page.get("properties", {})
            matches_by_id[page.get("id", "")] = {
                "page_id": page.get("id"),
                "url": page.get("url"),
                "title": notion_property_text(properties.get(title_property[0], {})) if title_property else "",
                "doi": notion_property_text(properties.get(doi_property[0], {})) if doi_property else "",
            }

    return json.dumps(
        {
            "query": {"title": title, "doi": canonical_doi},
            "matches": list(matches_by_id.values()),
            "is_duplicate": bool(matches_by_id),
        },
        ensure_ascii=False,
    )


@function_tool
def push_search_article(
    title: str,
    authors: str = "",
    year: str = "",
    venue: str = "",
    doi: str = "",
    official_url: str = "",
    abstract: str = "",
    source_type: str = "",
    ticket_id: str = "",
    relevance_note: str = "",
) -> str:
    """Create a selected literature candidate in the Notion search database.

    The database schema is read at runtime. Recognized fields are populated when they
    exist; unknown custom properties are left untouched. An existing title or DOI is
    skipped, making retries safe. Use only for selected candidates, not raw results.
    """
    title = title.strip()
    if not title:
        return "Error: title must not be empty."
    database_id = os.getenv("NOTION_DATABASE_SEARCH_ID")
    if not database_id:
        return "Error: Missing NOTION_DATABASE_SEARCH_ID in .env"

    try:
        headers = notion_headers()
        schema_response = requests.get(
            f"https://api.notion.com/v1/databases/{database_id}", headers=headers, timeout=20
        )
        schema_response.raise_for_status()
        schema = schema_response.json().get("properties", {})
    except (RuntimeError, requests.RequestException) as exc:
        return f"Error: Could not inspect the literature-search database: {exc}"

    title_property = find_schema_property(schema, ("title", "paper title", "article title", "name")) or first_title_property(schema)
    if not title_property:
        return "Error: The literature-search database has no title property."
    doi_property = find_schema_property(schema, ("doi",))

    for name, definition, value in (
        (doi_property[0], doi_property[1], doi) if doi_property and doi else ("", {}, ""),
        (title_property[0], title_property[1], title),
    ):
        filter_payload = source_search_filter(name, definition, value) if name and value else None
        if not filter_payload:
            continue
        try:
            response = requests.post(
                f"https://api.notion.com/v1/databases/{database_id}/query",
                headers=headers,
                json={"filter": filter_payload, "page_size": 1},
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return f"Error: Could not check for existing search records: {exc}"
        pages = response.json().get("results", [])
        if pages:
            return json.dumps(
                {"status": "skipped", "title": title, "reason": "An article with this title or DOI already exists.", "page_id": pages[0].get("id")},
                ensure_ascii=False,
            )

    values = {
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "doi": doi,
        "official_url": official_url,
        "abstract": abstract,
        "source_type": source_type,
        "ticket_id": ticket_id,
        "relevance_note": relevance_note,
    }
    aliases = {
        "title": ("title", "paper title", "article title", "name"),
        "authors": ("authors", "author"),
        "year": ("year", "publication year"),
        "venue": ("venue", "journal", "publication", "container title"),
        "doi": ("doi",),
        "official_url": ("official url", "url", "link", "source url"),
        "abstract": ("abstract", "summary"),
        "source_type": ("source type", "type", "publication type"),
        "ticket_id": ("ticket id", "ticket_id"),
        "relevance_note": ("relevance note", "relevance", "notes", "note"),
    }
    properties: dict[str, Any] = {}
    for field, value in values.items():
        match = title_property if field == "title" else find_schema_property(schema, aliases[field])
        if not match:
            continue
        property_value = notion_text_property(match[1].get("type", ""), value)
        if property_value:
            properties[match[0]] = property_value

    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json={"parent": {"database_id": database_id}, "properties": properties},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return f"Error: Could not create literature-search record: {exc}"

    page = response.json()
    return json.dumps(
        {"status": "created", "title": title, "page_id": page.get("id"), "url": page.get("url"), "populated_properties": list(properties)},
        ensure_ascii=False,
    )


@function_tool
def pull_notion_ticket(ticket_id: str) -> str:
    """
    Pull a thesis improvement ticket from the Notion improvement-tickets database.

    Use this when the user asks to pull, inspect, explain, or summarize a ticket.
    """

    try:
        pages = find_ticket_pages(ticket_id, notion_headers())
    except (RuntimeError, requests.RequestException) as exc:
        return f"Error: Could not query Notion database: {exc}"

    if not pages:
        return f"No ticket found with ticket_id={ticket_id!r}."

    # Step 2: Deduplicate by ticket_id.
    tickets_by_id: dict[str, dict[str, str]] = {}

    for page in pages:
        ticket = extract_ticket_from_page(page)
        found_id = ticket.get("ticket_id")

        if found_id and found_id not in tickets_by_id:
            tickets_by_id[found_id] = ticket

    ticket = tickets_by_id.get(ticket_id)

    if not ticket:
        return (
            f"Found {len(pages)} page(s), but none had an exact parsed "
            f"ticket_id={ticket_id!r}."
        )

    return json.dumps(ticket, indent=2, ensure_ascii=False)


@function_tool
def push_notion_ticket(
    ticket_id: str,
    severity: str,
    issue_type: str,
    confidence: str,
    location: str,
    diagnosis: str,
    evidence: str,
    why_it_matters: str,
    suggested_research_directions: str,
    expected_improvement: str,
) -> str:
    """Create a thesis improvement ticket in Notion unless its ticket_id already exists.

    Pass list fields as newline bullet text. This tool checks the configured database for
    the ticket ID before creating a page, so it is safe to retry after an interrupted run.
    """
    if not ticket_id.strip():
        return "Error: ticket_id must not be empty."

    database_id = os.getenv("NOTION_DATABASE_TICKET_ID")
    if not database_id:
        return "Error: Missing NOTION_DATABASE_TICKET_ID in .env"

    try:
        headers = notion_headers()
        existing_pages = find_ticket_pages(ticket_id, headers)
    except (RuntimeError, requests.RequestException) as exc:
        return f"Error: Could not query Notion database before creating ticket: {exc}"

    if existing_pages:
        return json.dumps(
            {
                "status": "skipped",
                "ticket_id": ticket_id,
                "reason": "A ticket with this ticket_id already exists.",
                "page_id": existing_pages[0].get("id"),
            },
            ensure_ascii=False,
        )

    properties = {
        "ticket_id": {"title": text_blocks(ticket_id, TITLE_CHUNK_SIZE)},
        "severity": {"select": {"name": severity}},
        "issue_type": {"select": {"name": issue_type}},
        "confidence": {"select": {"name": confidence}},
        "location": {"rich_text": text_blocks(location)},
        "diagnosis": {"rich_text": text_blocks(diagnosis)},
        "evidence": {"rich_text": text_blocks(evidence)},
        "why_it_matters": {"rich_text": text_blocks(why_it_matters)},
        "suggested_research_directions": {
            "rich_text": text_blocks(suggested_research_directions)
        },
        "expected_improvement": {"rich_text": text_blocks(expected_improvement)},
    }

    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json={"parent": {"database_id": database_id}, "properties": properties},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return f"Error: Could not create Notion ticket: {exc}"

    page = response.json()
    created_id = extract_ticket_from_page(page).get("ticket_id")
    result = {
        "status": "created",
        "ticket_id": ticket_id,
        "page_id": page.get("id"),
        "url": page.get("url"),
        "verified_ticket_id": created_id,
    }
    if created_id != ticket_id:
        result["warning"] = "The created page did not return the expected ticket_id."
    return json.dumps(result, ensure_ascii=False)
