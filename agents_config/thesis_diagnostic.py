from agents import Agent, ModelSettings

from app.skills import load_skill

from tools.notion import pull_notion_ticket, push_notion_ticket
from tools.github import (
    clone_or_update_thesis_repository,
)
from tools.latex import (
    list_repo_files,
    read_repo_file,
    search_repo_text,
)


def create_thesis_diagnostic_agent(model):
    return Agent(
        name="Thesis Diagnostic Reviewer",
        instructions=load_skill("skills/thesis-diagnostic-reviewer.md"),
        model=model,
        model_settings=ModelSettings(
            include_usage=True,
            parallel_tool_calls=False,
            ),
        tools=[
            clone_or_update_thesis_repository,
            list_repo_files,
            read_repo_file,
            search_repo_text,
            pull_notion_ticket,
            push_notion_ticket,
        ],
    )
