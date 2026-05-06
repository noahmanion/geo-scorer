# Roadmap: Firecrawl GEO Intelligence PoC

## Overview

The PoC delivers a measurement pipeline that runs a structured battery of developer-intent queries against four LLMs, scores every response for competitor mentions using Firecrawl's structured extraction, aggregates results into normalized GEO scores, and surfaces the competitive landscape through a static dashboard deployed on Vercel. All v1 requirements were delivered in a single PoC push, organized here into two coherent phases: the data collection and scoring pipeline, then the analysis, visualization, and audit layer built on top of it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Collection & Scoring** - Run query battery against 4 LLMs, persist responses to SQLite, score each response per competitor via Firecrawl structured extraction
- [x] **Phase 2: Analysis, Dashboard & Audit** - Compute and normalize GEO scores, publish static dashboard on Vercel, validate parser accuracy with spot-check tool

## Phase Details

### Phase 1: Data Collection & Scoring
**Goal**: Operators can run a structured query battery against Claude, GPT, Gemini, and Perplexity; all responses and competitor scores are durably persisted to SQLite with resume-from-failure support
**Depends on**: Nothing (first phase)
**Requirements**: COLL-01, COLL-02, COLL-03, COLL-04, SCOR-01, SCOR-02, SCOR-03, SCOR-04
**Success Criteria** (what must be TRUE):
  1. Running `python -m geo.orchestrator` executes the full 38-query battery across all 4 LLM models and persists every response to SQLite
  2. Re-running the orchestrator after a partial failure resumes from where it left off without duplicating rows
  3. Running with `--dry-run` prints the planned execution matrix without making any API calls
  4. Running with `--models` or `--queries` flags filters the battery to the specified subset
  5. Each LLM response is scored for every competitor (mention, position, strength, context quality, confidence, evidence quote) via one Firecrawl parser call per competitor, with up to 3 retry attempts on transient failures
**Plans**: TBD

### Phase 2: Analysis, Dashboard & Audit
**Goal**: Operators can view Firecrawl's GEO ranking versus competitors on a live Vercel dashboard, with confidence in parser accuracy backed by a spot-check audit tool
**Depends on**: Phase 1
**Requirements**: ANLY-01, ANLY-02, ANLY-03, ANLY-04, DASH-01, DASH-02, DASH-03, DASH-04, AUDT-01, AUDT-02
**Success Criteria** (what must be TRUE):
  1. Running `python -m geo.score` computes GEO scores per (model, segment, competitor) cell using the weighted formula and normalizes them 0-10 across the full matrix
  2. The Vercel dashboard shows Firecrawl's headline GEO score and rank, a horizontal bar chart of all competitors, and a grouped bar chart broken down by query segment
  3. The dashboard loads its data from `dashboard/data.json` without a backend server and is accessible at the deployed Vercel URL
  4. Running the spot-check tool samples 30 random (response, score) pairs for manual review and saves results with an agreement rate to `data/spot_check.json`
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Collection & Scoring | TBD | Complete | 2026-05-06 |
| 2. Analysis, Dashboard & Audit | TBD | Complete | 2026-05-06 |
