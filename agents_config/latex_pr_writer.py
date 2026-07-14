from agents import Agent, ModelSettings

from app.skills import load_skill

from tools.latex import (
    list_repo_files,
    read_repo_file,
    search_repo_text,
)
from tools.github import clone_or_update_thesis_repository
from tools.notion import list_search_articles, pull_notion_ticket
from tools.mendeley_download import download_mendeley_pdf
from tools.thesis_writer import (
    commit_writer_changes,
    create_writer_branch,
    replace_thesis_text,
    validate_writer_changes,
    push_writer_branch,
    create_writer_pull_request,
)


def create_latex_pr_writer_agent(model):
    return Agent(
        name="Thesis LaTeX Writer",
        instructions=load_skill("skills/thesis-latex-pr-writer.md"),
        model=model,
        model_settings=ModelSettings(include_usage=True, parallel_tool_calls=False),
        tools=[
            clone_or_update_thesis_repository,

            list_repo_files,
            read_repo_file,
            search_repo_text,

            pull_notion_ticket,
            list_search_articles,
            download_mendeley_pdf,

            replace_thesis_text,

            create_writer_branch,
            validate_writer_changes,
            commit_writer_changes,
            push_writer_branch,
            create_writer_pull_request,
        ],
    )
