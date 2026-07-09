import os
import requests
import json
from typing import Any

from agents import function_tool

NOTION_VERSION = "2022-06-28"


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


@function_tool
def pull_notion_ticket(ticket_id: str) -> str:
    """
    Pull a thesis improvement ticket from the Notion improvement-tickets database.

    Use this when the user asks to pull, inspect, explain, or summarize a ticket.
    """

    database_id = os.getenv("NOTION_DATABASE_ID")

    if not database_id:
        return "Error: Missing NOTION_DATABASE_ID in .env"

    headers = notion_headers()

    # Step 1: Query existing rows for the requested ticket_id.
    query_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    payload = {
        "filter": {
            "property": "ticket_id",
            "title": {
                "equals": ticket_id,
            },
        },
        "page_size": 10,
    }

    try:
        query_response = requests.post(
            query_url,
            headers=headers,
            json=payload,
            timeout=20,
        )
        query_response.raise_for_status()
    except requests.RequestException as exc:
        return f"Error: Could not query Notion database: {exc}"

    data = query_response.json()
    pages = data.get("results", [])

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
