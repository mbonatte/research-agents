from agents import Agent, ModelSettings

from app.skills import load_skill

from tools.github import clone_or_update_thesis_repository
from tools.latex import (
    list_repo_files,
    read_repo_file,
    search_repo_text,
)
from tools.notion import (
    list_search_articles,
    pull_notion_ticket,
    write_literature_fit_review,
    write_ticket_literature_fit_summary,
)


def create_literature_reviewer_agent(model):
    return Agent(
        name="Literature Fit Reviewer",
        instructions=load_skill("skills/thesis-literature-fit-reviewer.md"),
        model=model,
        model_settings=ModelSettings(include_usage=True, parallel_tool_calls=False),
        tools=[
            clone_or_update_thesis_repository,
            list_repo_files,
            read_repo_file,
            search_repo_text,
            pull_notion_ticket,
            list_search_articles,
            write_literature_fit_review,
            write_ticket_literature_fit_summary,
        ],
    )
