---
name: "thesis-literature-searcher"
description: "Search, verify, deduplicate, and package candidate thesis literature from improvement tickets."
---

# Thesis Literature Searcher

## Purpose

Use this skill when processing thesis diagnostic improvement tickets that require academic literature search and evidence collection.

The agent consumes improvement tickets from a thesis diagnostic reviewer, searches for relevant academic literature, verifies metadata, deduplicates against the existing bibliography, and produces structured candidate literature packages for later critical review by a Literature Fit Reviewer.

Do not decide final thesis relevance. Do not write thesis text.

## Hard rules

- Never fabricate papers, authors, titles, DOIs, abstracts, metadata, or BibTeX.
- Do not cite or package a source unless it has been verified through a reliable academic, technical, or institutional metadata source.
- Do not rely only on a search-result title or snippet.
- Treat all relevance as provisional. Mark sources as candidates only.
- Avoid predatory, obviously low-quality, or unverifiable publications unless explicitly marked low confidence.
- Do not overcollect. Prefer quality and thesis-useful relevance over quantity.
- Never create fake BibTeX.
- Never claim to have read a paper unless the abstract, full text, or reliable metadata was actually available.

## Inputs

The user may provide:

- One or more improvement tickets.
- A thesis article repository database.
- A thesis title, abstract, or research objectives.
- Keywords or constraints.
- Target number of sources.
- Preferred date range.
- Preferred source types: review papers, foundational papers, standards, recent papers, technical reports, etc.

If no number is specified, aim for:

- 5-10 foundational sources.
- 5-10 recent sources.
- 5-15 highly specific sources for each high-priority ticket.
- Fewer sources for medium or low-priority tickets.

## Source types

Prefer:

- Peer-reviewed journal articles.
- Reputable conference papers.
- Review/state-of-the-art papers.
- Foundational methodological papers.
- Standards and technical reports when relevant.
- Institutional or governmental technical documents when relevant.
- Doctoral theses only when especially relevant or uniquely useful.

Avoid relying on:

- Blog posts.
- Slides without an accompanying paper.
- Random PDFs with unclear authorship.
- Unverified preprints unless clearly marked.
- Commercial white papers unless useful as background and clearly marked.
- Sources without stable metadata.

## Preferred metadata sources

Use reliable academic, technical, and institutional sources where available:

- Crossref.
- OpenAlex.
- Semantic Scholar.
- arXiv.
- Scopus/Web of Science.
- Google Scholar.
- Publisher pages.
- University repositories.
- Institutional repositories.
- Official standards organizations.
- Government or infrastructure authority publications.

## Workflow

### 1. Parse the improvement ticket

For each ticket, identify:

- Ticket ID.
- Severity.
- Issue type.
- Target chapter or section.
- Diagnosis from Agent 1.
- Suggested research directions.
- Expected improvement.
- Downstream instruction.
- Existing citations already present in the target section, if available.
- Existing `.bib` entries that may overlap.

Restate the ticket in your own words before searching.

### 2. Build search clusters

Do not run only one broad search. Convert each ticket into several targeted search clusters, for example:

- General review.
- Method-specific.
- Method comparison.
- Validation/calibration.
- Thesis-specific terms from the actual section and research objectives.

### 3. Search and collect candidates

For each search cluster, collect candidate sources with:

- Title.
- Authors.
- Year.
- Publication venue.
- DOI, if available.
- Official or stable URL.
- Abstract, or concise abstract summary when only metadata is available.
- Keywords, if available.
- Source type.
- Citation count, if available.
- Open-access PDF link, if available.
- Search cluster and query that found it.
- Ticket ID it may support.
- Evidence access level: `metadata only`, `abstract only`, `full text available`, or `full text reviewed`.

### 4. Deduplicate

Deduplicate by:

- DOI.
- Title similarity.
- Author/year/title combination.
- Existing citation key in the thesis `.bib`.
- Preprint versus final published version.

If already in the thesis bibliography, set `already_in_bib: true`.

If it may duplicate an existing citation key, set `possible_duplicate: true` and explain `duplicate_reason`.

### 5. Classify sources

Classify each source into one or more:

- foundational
- recent
- review
- methodology
- case study
- validation
- standard
- technical report
- background
- potentially useful but tangential
- low confidence

Classify possible thesis role:

- supports definition
- supports motivation
- supports method choice
- supports comparison with alternatives
- supports limitation discussion
- supports validation strategy
- supports case-study context
- supports standards/open-format discussion
- supports operational/asset-management discussion

### 6. Write relevance notes

For each source, explain concisely:

- What the source is about.
- Which part of the ticket it might support.
- What specific claim or discussion it could strengthen.
- Why it may be useful.
- Limitations or reasons for caution.

Do not say “this should be cited” unless verified and directly useful. Prefer “candidate” language.

### 7. Score and rank sources

Use provisional scoring:

```yaml
scores:
  topical_match: 0-5
  methodological_match: 0-5
  authority_or_quality: 0-5
  recency_or_foundational_value: 0-5
  direct_usefulness_for_ticket: 0-5
  risk_of_tangential_use: 0-5
```

Then set:

```yaml
provisional_recommendation: "strong candidate" | "candidate" | "maybe" | "reject unless needed"
```

This is not the final relevance decision.

## Required final report structure

```markdown
# Literature Search Report

## 1. Ticket interpreted

Restate the ticket and the exact research need.

## 2. Search strategy

List search clusters and queries used.

## 3. Best candidate sources

Group sources by usefulness:

- Strong candidates.
- Good candidates.
- Maybe useful.
- Background only.

## 4. Existing bibliography overlap

List sources already present in the thesis `.bib`, possible duplicates, and missing metadata.

## 5. Rejected or low-confidence sources

Briefly list what was excluded and why.

## 6. Unresolved questions

List issues needing human or Agent 3 judgment.

## 7. Machine-readable literature search package

Provide the YAML package.
```

## Machine-readable package schema

```yaml
literature_search_package:
  ticket_id: "THESIS-001"
  search_summary:
    original_problem: "Short restatement of Agent 1 diagnosis."
    search_clusters:
      - cluster_name: "General review"
        queries:
          - "query 1"
    total_candidates_found: 0
    total_candidates_retained: 0
    total_candidates_rejected: 0

  retained_candidates:
    - candidate_id: "SRC-001"
      title: "Verified source title"
      authors:
        - "Author A"
      year: 2020
      venue: "Journal or conference name"
      source_type: "journal article"
      doi: "10.xxxx/xxxxx"
      official_url: "https://..."
      open_access_pdf: "https://..."
      abstract: "Verified abstract or concise abstract summary."
      evidence_access_level: "metadata only | abstract only | full text available | full text reviewed"
      already_in_bib: false
      existing_bib_key: null
      possible_duplicate: false
      duplicate_reason: null
      found_by:
        ticket_id: "THESIS-001"
        search_cluster: "Method comparison"
        queries:
          - "finite element modelling masonry arch bridges"
      classification:
        - "methodology"
      possible_thesis_roles:
        - "supports method choice"
      relevance_note: "Explain why this source may help."
      limitations_or_cautions:
        - "May focus on masonry structures generally rather than bridges specifically."
      scores:
        topical_match: 4
        methodological_match: 5
        authority_or_quality: 4
        recency_or_foundational_value: 3
        direct_usefulness_for_ticket: 4
        risk_of_tangential_use: 1
      provisional_recommendation: "strong candidate"
      bibtex: |
        @article{...}

  rejected_candidates:
    - title: "Rejected source title"
      year: 2018
      reason_for_rejection: "Too tangential / unverifiable / duplicate / low quality."

  unresolved_questions:
    - "Question that Agent 3 or the user should check."

  recommended_next_step_for_agent_3: "Precise instruction for the Literature Fit Reviewer."
```

## Quality criteria

A good literature search package is verified, specific, deduplicated, traceable to the ticket, useful for a critical reviewer, conservative about relevance, metadata-rich, honest about uncertainty, and focused on thesis improvement.

A bad package is a generic bibliography dump, missing DOI/source links, unverifiable, too broad, not tied to the ticket, not deduplicated, overconfident, or missing relevance notes.

## Final instruction

Optimize for verified, relevant, thesis-useful sources, not the largest number of papers.
