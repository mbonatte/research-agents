# PhD Researcher Agents

Local command-line agents for supporting PhD thesis work. The current draft focuses on interactive research and thesis-review workflows backed by the OpenAI Agents SDK, configurable model providers, a private thesis GitHub repository, and a Notion thesis-improvement database.

## Current Capabilities

- Start an interactive terminal chat with a selected thesis agent.
- Run a thesis diagnostic reviewer against files from a cloned thesis repository.
- Pull thesis-improvement tickets from a Notion database.
- Create deduplicated thesis-improvement tickets in Notion after a diagnostic run.
- Run standalone deep, multi-source academic searches with OpenAlex, Crossref,
  Semantic Scholar, arXiv, and DOI/BibTeX verification.

The currently registered agents are:

- `diagnostic`: reviews thesis content using the local thesis repository and Notion tickets.
- `searcher`: searches for literature related to a thesis ticket or research question.
- `reviewer`: assesses selected sources against thesis context and records fit decisions.
- `writer`: applies approved sources as small, validated local LaTeX/BibTeX changes.

Additional agent configs and skills are present in the repo but are not yet be registered in `agents_config/registry.py`.

## Repository Layout

```text
.
|-- agents_config/    Agent definitions and registry
|-- app/              Shared runtime helpers for models, chat, logging, and skills
|-- skills/           Agent instruction files
|-- tools/            Tool functions exposed to agents
|-- main.py           Interactive CLI entry point
|-- env.example       Environment variable template
|-- requirements.txt  Python dependencies
```

Local runtime folders are intentionally ignored by Git:

- `.runs/`: saved agent run logs.
- `.secrets/`: generated or local secret files.
- `.venv/`: local Python virtual environment.
- `repositories/`: cloned external repositories, including the thesis repository.

## Quickstart

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a local `.env` file from the example:

Fill in the required values in `.env`, then run:

```powershell
python main.py
```

The CLI prints the available agents and asks which one to run.

## Environment Variables

The draft `.env` template is in `env.example`.

Required for the default model in `main.py`:

- `NVIDIA_API_KEY`: API key for the NVIDIA-hosted OpenAI-compatible endpoint.

Optional or tool-specific:

- `GEMINI_API_KEY`: API key for the Gemini OpenAI-compatible endpoint.
- `NOTION_API_KEY_PHD_THESIS`: Notion integration token for the thesis database.
- `NOTION_DATABASE_TICKET_ID`: Notion database ID for thesis-improvement tickets.
- `NOTION_DATABASE_MENDELEY_ID`: Notion database ID for Mendeley records.
- `NOTION_DATABASE_SEARCH_ID`: Notion database ID for literature searches.
- `GITHUB_PHD_THESIS_URL`: SSH clone URL for the private thesis repository.
- `GITHUB_PHD_THESIS_KEY_PRIVATE`: base64-encoded SSH private key used by the GitHub tool.
- `GITHUB_ACCESS_TOKEN`: currently reserved for GitHub access-token workflows.

The non-agent helper `tools.notion.update_mendeley_article` creates or updates a
Mendeley archive record by page ID, Mendeley ID, DOI, or title. It maps only properties
available in the configured Notion schema.

## Planned Setup Documentation

These sections are intentionally left as the next documentation milestones before the workflow is treated as reproducible.

### GitHub Thesis Repository Setup

TODO:

- Create or identify the private thesis repository.
- Add the correct SSH deploy key or access token.
- Encode the private key for `GITHUB_PHD_THESIS_KEY_PRIVATE`.
- Set `GITHUB_PHD_THESIS_URL`.
- Verify that `clone_or_update_thesis_repository` clones into `repositories/thesis`.

### Notion Database Setup

TODO:

- Create the thesis-improvement database.
- Define the expected ticket properties, including `ticket_id`, `severity`, `issue_type`, `confidence`, `location`, `diagnosis`, `evidence`, `why_it_matters`, `suggested_research_directions`, and `expected_improvement`.
- Create a Notion integration and share the database with it.
- Set `NOTION_API_KEY_PHD_THESIS` and `NOTION_DATABASE_TICKET_ID`.
- Verify that `pull_notion_ticket` can retrieve a known ticket and that a diagnostic
  run can create a new ticket. Ticket creation skips an existing `ticket_id`, making
  retries safe.

### AI Provider Token Setup

TODO:

- Document how to create the NVIDIA API key used by `create_nvidia_model`.
- Document how to create the Gemini API key used by `create_gemini_model`.
- Decide which model provider should be the default in `main.py`.
- Document any provider-specific rate limits, model names, and expected costs.

## Development Notes

- Agent behavior is primarily controlled by Markdown instruction files in `skills/`.
- New agents should be registered in `agents_config/registry.py` before they appear in the CLI.
- Tool functions exposed to agents should use `@function_tool` from the OpenAI Agents SDK.
