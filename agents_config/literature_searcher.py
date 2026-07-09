from agents import Agent, ModelSettings

from agents import WebSearchTool

from app.skills import load_skill

from tools.notion import pull_notion_ticket

from tools.academic import (
    search_openalex,
#     get_openalex_work,
#     search_crossref,
#     get_crossref_work,
#     search_semantic_scholar,
#     get_semantic_scholar_paper,
#     search_arxiv,
#     normalize_doi,
#     validate_doi,
#     get_bibtex_from_doi,
#     find_open_access_pdf,
)

# from tools.bibliography import (
#     list_bib_files,
#     parse_bibtex_entries,
#     find_bibtex_duplicates,
# )

def create_literature_searcher_agent(model):
    return Agent(
        name="Literature Searcher",
        instructions=load_skill("skills/thesis-literature-searcher.md"),
        model=model,
        model_settings=ModelSettings(include_usage=True),
        tools=[
            # WebSearchTool(),

            # Ticket context
            pull_notion_ticket,

            # Thesis repository / bibliography context
            # list_repo_files,
            # read_repo_file,
            # search_repo_text,
            # list_bib_files,
            # parse_bibtex_entries,
            # find_bibtex_duplicates,

            # Academic discovery
            search_openalex,
            # get_openalex_work,
            # search_crossref,
            # get_crossref_work,
            # search_semantic_scholar,
            # get_semantic_scholar_paper,
            # search_arxiv,

            # Verification / export
            # normalize_doi,
            # validate_doi,
            # get_bibtex_from_doi,
            # find_open_access_pdf,
        ],
    )