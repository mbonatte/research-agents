from agents import Agent, ModelSettings

from app.skills import load_skill
from tools.academic import (
    get_bibtex_from_doi,
    get_crossref_work,
    get_openalex_work,
    search_arxiv,
    search_crossref,
    search_openalex,
    search_semantic_scholar,
)
from tools.notion import check_mendeley_archive, pull_notion_ticket, push_search_article
from tools.web_fetch import fetch_website_text


def create_literature_searcher_agent(model):
    return Agent(
        name="Literature Searcher",
        instructions=load_skill("skills/thesis-literature-searcher.md"),
        model=model,
        model_settings=ModelSettings(include_usage=True, parallel_tool_calls=False),
        tools=[
            pull_notion_ticket,
            check_mendeley_archive,
            push_search_article,
            search_openalex,
            get_openalex_work,
            search_crossref,
            get_crossref_work,
            search_semantic_scholar,
            search_arxiv,
            get_bibtex_from_doi,
            fetch_website_text,
        ],
    )
