import asyncio
import json

import pytest

from tools import notion
from tools.mendeley import mendeley_document_to_archive_record


class Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise notion.requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture(autouse=True)
def notion_environment(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY_PHD_THESIS", "test-token")
    monkeypatch.setenv("NOTION_DATABASE_TICKET_ID", "tickets")
    monkeypatch.setenv("NOTION_DATABASE_MENDELEY_ID", "mendeley")
    monkeypatch.setenv("NOTION_DATABASE_SEARCH_ID", "search")


def invoke(tool, **arguments):
    context = type("ToolContext", (), {"tool_name": tool.name, "run_config": None})()
    return asyncio.run(tool.on_invoke_tool(context, json.dumps(arguments)))


def test_text_blocks_and_schema_matching():
    blocks = notion.text_blocks("a" * 2001)
    assert [len(block["text"]["content"]) for block in blocks] == [2000, 1]
    schema = {"Ticket_ID": {"type": "rich_text"}}
    assert notion.find_schema_property(schema, ("ticket id",))[0] == "Ticket_ID"


def test_mendeley_document_mapper_prefers_pdf_and_preserves_sync_fields():
    record = mendeley_document_to_archive_record(
        {"id": "doc-1", "title": "Paper", "authors": [{"first_name": "Ada", "last_name": "Lovelace"}],
         "identifiers": {"doi": "10.1/example"}, "citation_key": "Lovelace2026",
         "keywords": ["bridges"], "tags": ["review"], "last_modified": "2026-01-01T00:00:00Z"},
        {"doc-1": [{"id": "other", "mime_type": "text/plain"}, {"id": "pdf", "mime_type": "application/pdf"}]},
    )
    assert record["authors"] == "Ada Lovelace"
    assert record["file_id"] == "pdf"
    assert record["doi"] == "10.1/example"


def test_push_ticket_skips_existing_record(monkeypatch):
    monkeypatch.setattr(
        notion.requests,
        "post",
        lambda *args, **kwargs: Response({"results": [{"id": "existing-page"}]}),
    )
    result = json.loads(invoke(
        notion.push_notion_ticket,
        ticket_id="TEST-1", severity="low", issue_type="quality", confidence="high",
        location="cover", diagnosis="fixed date", evidence="source", why_it_matters="stale",
        suggested_research_directions="", expected_improvement="dynamic date",
    ))
    assert result == {
        "status": "skipped", "ticket_id": "TEST-1",
        "reason": "A ticket with this ticket_id already exists.", "page_id": "existing-page",
    }


def test_update_mendeley_article_creates_when_no_match(monkeypatch):
    schema = {"Name": {"type": "title"}, "DOI": {"type": "rich_text"}, "Abstract": {"type": "rich_text"}}
    calls = []
    monkeypatch.setattr(notion.requests, "get", lambda *args, **kwargs: Response({"properties": schema}))

    def post(url, **kwargs):
        calls.append((url, kwargs.get("json")))
        if url.endswith("/query"):
            return Response({"results": []})
        return Response({"id": "new-page", "url": "https://notion.so/new-page"})

    monkeypatch.setattr(notion.requests, "post", post)
    result = notion.update_mendeley_article(title="A source", doi="10.1000/example", abstract="Verified abstract")
    assert result["status"] == "created"
    create_payload = calls[-1][1]
    assert create_payload["properties"]["Name"]["title"][0]["text"]["content"] == "A source"
    assert "Abstract" in create_payload["properties"]


def test_list_search_articles_filters_ticket(monkeypatch):
    schema = {"Name": {"type": "title"}, "Ticket ID": {"type": "rich_text"}}
    page = {
        "id": "candidate-1", "url": "https://notion.so/candidate-1",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Paper"}]},
            "Ticket ID": {"type": "rich_text", "rich_text": [{"plain_text": "T-1"}]},
        },
    }
    monkeypatch.setattr(notion.requests, "get", lambda *args, **kwargs: Response({"properties": schema}))
    monkeypatch.setattr(notion.requests, "post", lambda *args, **kwargs: Response({"results": [page]}))
    result = json.loads(invoke(notion.list_search_articles, ticket_id="T-1"))
    assert result[0]["page_id"] == "candidate-1"
    assert result[0]["title"] == "Paper"


def test_write_fit_review_adds_missing_properties_and_updates_page(monkeypatch):
    calls = []
    monkeypatch.setattr(notion.requests, "get", lambda *args, **kwargs: Response({"properties": {}}))

    def patch(url, **kwargs):
        calls.append((url, kwargs.get("json")))
        if "/databases/" in url:
            return Response({"properties": kwargs["json"]["properties"]})
        return Response({"id": "candidate-1", "url": "https://notion.so/candidate-1"})

    monkeypatch.setattr(notion.requests, "patch", patch)
    result = json.loads(invoke(
        notion.write_literature_fit_review,
        page_id="candidate-1", fit_decision="accept", evidence_access="abstract only",
        citation_use="supporting citation", summary="Relevant and verified.",
    ))
    assert result["status"] == "updated"
    assert "Fit Decision" in calls[0][1]["properties"]
    assert calls[1][1]["properties"]["Fit Decision"]["select"]["name"] == "accept"
