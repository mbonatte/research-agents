from agents import Agent, ModelSettings

from app.skills import load_skill

from tools.latex import (
    list_repo_files,
    read_repo_file,
    search_repo_text,
)


def create_latex_pr_writer_agent(model):
    return Agent(
        name="Literature Fit Reviewer",
        instructions=load_skill("skills/thesis-latex-pr-writer.md"),
        model=model,
        model_settings=ModelSettings(include_usage=True),
        tools=[
            list_repo_files,
            read_repo_file,
            search_repo_text,
        ],
    )