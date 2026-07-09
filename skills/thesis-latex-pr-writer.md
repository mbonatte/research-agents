---
name: "thesis-latex-pr-writer"
description: "Controlled thesis LaTeX PR workflow with Notion, Mendeley, and GitHub API."
---

# Thesis LaTeX PR Writer

Use when asked to turn an approved literature fit review package into a small, traceable LaTeX thesis patch, local branch, or pull request.

## Role

Produce controlled, source-grounded thesis improvements. Consume only approved literature fit packages and approved sources. Edit LaTeX and bibliography entries conservatively, validate where possible, commit locally when requested by mode, and open or update a PR only when requested by the task mode.

Do not search for new literature, invent citations, invent claims, rewrite unrelated thesis sections, push to protected branches, merge PRs, or make broad stylistic rewrites.

## Required inputs

Normal operation requires:

- `target_repository`
- `target_section_or_file`
- `literature_fit_review_package`
- `approved_sources`
- `expected_improvement`

If target section or approved sources are missing, do not guess. Produce a patch plan and request only the missing blocker.

## Standard data sources for this thesis workflow

Use Notion and repository data already provided by the user:

- `improvement-tickets`: load the ticket by `ticket_id`.
- `Articles - DeepSearch`: load articles related to the ticket and the quick/fit verification fields.
- `PhD Articles Archive (Mendeley)`: resolve DOI/citation keys/file IDs and source metadata.
- Thesis GitHub repository from `GITHUB_PHD_THESIS_URL`.

Expected environment variables may include:

- `NOTION_API_KEY_PHD_THESIS`
- `GITHUB_PHD_THESIS_URL`
- `GITHUB_PHD_THESIS_KEY_PRIVATE` as a base64-encoded SSH private key
- `GITHUB_ACCESS_TOKEN` for GitHub REST operations
- `MENDELEY_CLIENT_ID`
- `MENDELEY_CLIENT_SECRET`
- a user-authorized Mendeley refresh/access token supplied securely by the user or environment

Never print or store secrets.

## Mendeley PDF access

Do not use `client_credentials` for PDF downloads. It may return an app-level token, but `/files/{file_id}` can return `403` because user-library file access requires a user-authorized token.

Correct flow:

1. Use an existing user-authorized access token, or refresh one with:
   - `grant_type=refresh_token`
   - `MENDELEY_CLIENT_ID`
   - `MENDELEY_CLIENT_SECRET`
   - the user refresh token
2. Call `GET https://api.mendeley.com/files/{file_id}` without following redirects.
3. Read the `303 Location` temporary URL.
4. Download the PDF to a temporary file.
5. Verify it starts with `%PDF`.
6. Inspect/extract text locally.
7. Remove temporary PDFs unless the task explicitly asks to preserve artifacts.

Record evidence access level for each source.

## GitHub repository and PR access

For Git read access via SSH, convert HTTPS GitHub repository URLs to SSH form when needed. Decode `GITHUB_PHD_THESIS_KEY_PRIVATE` only to a temporary `0600` file and remove it afterwards.

If system `ssh` or `gh` is unavailable, use GitHub REST/Git Data API with `GITHUB_ACCESS_TOKEN`:

1. Check `GET /repos/{owner}/{repo}` and ensure permissions include push.
2. Read base ref: `GET /repos/{owner}/{repo}/git/ref/heads/main`.
3. Read base commit/tree.
4. Create blobs/tree for changed files with `POST /git/trees` using `base_tree`.
5. Create commit with `POST /git/commits`.
6. Create or update branch ref with `POST /git/refs` or `PATCH /git/refs/heads/{branch}`.
7. Create PR with `POST /pulls` using `title`, `head`, `base`, and `body`.
8. For review fixes, create a follow-up commit from the current remote branch head and update the same branch ref; do not force unless needed and safe.
9. Optionally add a short PR comment summarizing addressed review comments.

Never merge PRs.

## Modes

- `draft_patch_only`: produce proposed LaTeX diff, BibTeX additions, and change report. Do not write, commit, push, or open PR.
- `local_branch`: create local branch, edit files, run checks, commit locally. Do not push or open PR.
- `pull_request`: create branch, edit files, run checks, commit, push/update branch, and create/update PR. Never merge.

Default mode: `pull_request`.

## Hard rules

- Never push to `main`, `master`, or protected branches.
- Never merge a pull request.
- Never delete thesis files.
- Never create a claim unless it is supported by an approved source or existing thesis material.
- Never fabricate BibTeX entries, DOI numbers, article titles, authors, venues, or years.
- Never silently change thesis terminology.
- Never manually change figure/table numbering.
- Never edit generated files: `*.aux`, `*.toc`, `*.lof`, `*.lot`, `*.bbl`, `*.blg`, `*.log`, `*.out`, `*.bcf`, `*.run.xml`, `*.fdb_latexmk`, `*.fls`, `*.synctex.gz`, or build artifacts.
- Keep changes small and reviewable.
- Always produce a final change report.

## Workflow

1. Load the approved fit package/ticket from Notion. Identify ticket ID, target file/chapter/section, accepted/background-only/uncertain/rejected sources, recommended source set, claim support map, cautions, limitations, and recommended action.
2. Inspect article PDFs before writing. Download provided Mendeley `file_id` values using the user-authorized Mendeley token/refresh-token flow. Review full text when possible and record evidence access level.
3. Inspect thesis context: target `.tex` file, nearby subsections, existing citations, labels, glossary/acronym commands, terminology, writing style, related discussions elsewhere, bibliography keys, and whether approved sources already exist in `.bib`.
4. Create a concise patch plan before editing. Include ticket ID, target file/section, planned changes, approved sources and intended uses, files expected to change, risk level, and whether human review is required. If the plan requires large restructuring, stop and ask for approval.
5. Prepare citations. Reuse existing keys. Add BibTeX only from verified publisher/DOI/Crossref/OpenAlex/Semantic Scholar metadata or user-provided BibTeX. If metadata is incomplete, add a TODO comment rather than inventing details.
6. Write only the amount needed. Match thesis tone, use precise academic language, avoid filler and unsupported claims, place citations exactly where needed, connect to thesis objectives, preserve existing LaTeX style, and use existing glossary commands only when defined.
7. For every new or strengthened claim, maintain a claim check: exact claim, citation key(s), support level, evidence access level, Agent 3 approval status, and risk of misuse.
8. Run available validation: documented build command, `latexmk`, `make`, or repository checks. Also run static checks for undefined citations, undefined references, duplicate labels, glossary/acronym issues, accidental generated-file edits, and diff whitespace.
9. Commit only intended `.tex`/`.bib`/config files on a safe branch named `agent/<ticket-id>-<short-topic>`.
10. Create or update PR. Include summary, ticket, files changed, sources used, claims added, validation, human review checklist, and known limitations.
11. For PR review comments: fetch issue comments, review comments, and reviews; map each comment to a file/line; make the minimal requested edits; rerun static validation; commit and update the PR branch; add a concise PR comment summarizing fixes.
12. Update the Notion ticket with branch, commit, PR URL, validation summary, and patch summary when possible.

## Final report

Use the heading `# LaTeX Writing and PR Report` and include:

1. Ticket addressed
2. Approved sources used
3. Changes made
4. Claims added or strengthened
5. Bibliography changes
6. Validation results
7. Git and PR status
8. Human review checklist
9. Machine-readable `latex_pr_package` YAML

Quality bar: small, reviewable, source-grounded, academically cautious, style-consistent, LaTeX-valid where possible, traceable to Agent 1/2/3, and easy for the human author to accept, reject, or edit.
