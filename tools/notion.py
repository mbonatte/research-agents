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
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        raise RuntimeError("Missing NOTION_DATABASE_ID in .env")

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

    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        return "Error: Missing NOTION_DATABASE_ID in .env"

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
