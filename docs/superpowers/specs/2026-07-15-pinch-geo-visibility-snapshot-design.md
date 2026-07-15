# Pinch GEO Visibility Snapshot — Design

**Date:** 2026-07-15
**Status:** Approved design, pre-implementation
**Owner:** Noah Manion

## Purpose

Re-target the existing **Firecrawl GEO Rank Tracker** (a working PoC in this repo) to measure
the AI-answer visibility of **Pinch** (pinchmed.com → bookpinch.com), a concierge / at-home
medical aesthetics service, versus whoever the AI engines actually recommend instead.

This is a **modification of an existing tool**, not a from-scratch build. The pipeline
(LLM clients → SQLite persistence → Firecrawl `/parse` LLM-as-judge → scoring → static
dashboard) is reused; the *targeting layer* (queries, competitors, brand) and *two subsystems*
(web grounding, city dimension) change.

The analysis is a **one-time snapshot**, anchored on **Chicago** (Pinch's main market), covering a
spread of live markets, with a methodology **repeatable for expansion** — adding a city is a
config change.

The founder's real question: *"When someone asks an AI for what we do, in our city, do we show
up?"*

## Starting Point (what already exists)

A complete, delivered PoC measuring Firecrawl vs. web-scraping competitors:

- `geo/llms.py` — unified clients for Claude, GPT, Gemini, Perplexity (plain completions, **no
  web grounding**).
- `geo/orchestrator.py` — runs `model × query × rep` battery, persists to SQLite with a UNIQUE
  constraint enabling idempotent resume-from-failure.
- `geo/parser.py` — Firecrawl `/parse` structured extraction as LLM-as-judge; Pydantic
  `CompetitorScore`; one call per (response, competitor) to avoid position bias.
- `geo/score.py` — weighted GEO formula (mention×3.0 + strength×2.0 + context×1.5 −
  position×0.3), normalized 0–10.
- `queries.json` — 38 developer-intent queries across 5 segments (flat, **no geography**).
- `competitors.json` — fixed list: Firecrawl, Apify, Browserbase, Bright Data, Zyte,
  ScrapingBee.
- `dashboard/` — static site (ranking + segment charts) on Vercel; `spot_check.py` audit tool.

## Non-Goals (YAGNI guardrails)

- No scheduler / always-on tracker. Manual CLI run; re-runnable but not automated.
- No historical trending beyond what a manual re-run produces.
- No live-updating dashboard, no auth, no hosted DB (local SQLite only, as today).
- No maintained hard-coded competitor list — competitors are **emergent** (see Scoring).

## Target & Market

- **Tracked brand:** Pinch — at-home Botox/wrinkle relaxers, dermal fillers, microneedling,
  HydraGlow facials, PDRN, and group "Pinch Party" events. Domain: `bookpinch.com`
  (`pinchmed.com` 301-redirects here).
- **Anchor city:** Chicago (IL). **Additional cities:** Phoenix (AZ), Denver (CO), Seattle (WA),
  Washington DC metro.
- **Full operating footprint** (reference for future expansion cities): IL, AZ, CO, WA, MA, MI,
  MN, DC, MD, VA.

## Key Methodological Decisions

1. **Web grounding is mandatory and is the biggest code change.** Firecrawl is in the models'
   training data, so the current ungrounded adapters could name it. Pinch is a small local
   startup the models don't know — ungrounded, they refuse or hallucinate. Every engine must be
   called with live web grounding:
   - Perplexity — already web-native (`sonar-pro`), no change.
   - OpenAI — Responses API with the `web_search` tool.
   - Gemini — `google_search` grounding.
   - Anthropic (Claude) — `web_search` tool.
2. **Emergent competitors, not a fixed list.** A hard-coded list breaks on the first new city.
   The parser extracts *every provider each answer names*; the competitor set falls out of the
   answers, per city.
3. **Repetition to beat stochasticity.** Each (query × city × engine) runs **N≈3** times so a
   metric is a rate, not a single draw. (Reuses the existing rep + UNIQUE-constraint machinery.)
4. **Presence Rate is the headline metric.** Objective per-answer yes/no, averaged. The existing
   rich signals (strength, position, context, citations) are retained as *diagnostics*, not
   blended into a 0–10 composite.

## Changes (delta from existing code)

| Component | Action | Detail |
|---|---|---|
| `geo/llms.py` | **Change (critical)** | Add web-search grounding to Claude, GPT, Gemini adapters. Perplexity unchanged. Normalize each response to include cited source URLs/domains. |
| `queries.json` | **Rewrite** | Replace 38 dev queries with ~6–7 consumer aesthetics templates using a `{city}` placeholder. |
| `cities.json` | **New** | Editable city list: Chicago + Phoenix + Denver + Seattle + DC. Adding a city = one line. |
| `competitors.json` | **Repurpose** | Firecrawl → **Pinch** as the tracked brand (name + aliases: `pinch`, `bookpinch`, `pinchmed`). No fixed competitor list — competitors are emergent. |
| `geo/parser.py` | **Extend** | Keep Firecrawl `/parse` judge. Extract: (a) is Pinch named? (b) the ranked list of *every* provider named (emergent competitors), (c) whether `bookpinch.com` is cited as a source. |
| `geo/orchestrator.py` | **Extend** | Add the city dimension to the run matrix and SQLite schema: `model × city × query × rep`. Preserve idempotent resume. |
| `geo/score.py` | **Re-headline** | Surface **Presence Rate** per (city, engine) as the headline. Keep rank / share-of-voice / citation rate as diagnostics. Drop the normalized 0–10 composite as the primary output. |
| `dashboard/` | **Rework** | Segment charts → **city × engine presence heatmap** + emergent competitor leaderboard per city + citation-gap view. |
| Firecrawl `/parse`, SQLite core, resume logic, `spot_check.py`, Vercel config | **Keep** | Reused as-is. |

## Query Set (city-parameterized, replaces dev queries)

`{city}` templates across buyer intents (~6–7):
- **Discovery:** "Who offers at-home / mobile Botox in {city}?"
- **Category intent:** "I want Botox but don't want to go into a clinic in {city} — what are my options?"
- **Service-specific:** "Where can I get at-home dermal fillers in {city}?"; "mobile microneedling {city}"
- **Occasion:** "Who hosts Botox parties in {city}?"
- **Brand-aware:** "Is Pinch (bookpinch.com) legit? What are the reviews?" — reputation when the
  AI is asked about Pinch directly. (Kept unless the user opts for discovery-only.)

Approximate volume: ~7 templates × 5 cities × 4 engines × 3 reps ≈ **420 grounded calls**.
Grounded calls (Perplexity / OpenAI / Gemini web search) cost more than plain completions.

## Data Model (SQLite, extends existing)

- `runs` — raw: (id, run_date, model, **city**, query_id, run_index, prompt, response_text,
  citations_json). UNIQUE on (run_date, model, city, query_id, run_index) for idempotent resume.
- `mentions` / scores — parsed: (run_id, pinch_present, pinch_rank, providers_json,
  bookpinch_cited).

## Scoring

- **Presence Rate (headline):** fraction of runs where Pinch is named, per city and per engine.
- **Rank (diagnostic):** Pinch's position among named providers, when present.
- **Share of Voice (diagnostic):** Pinch mentions ÷ all provider mentions.
- **Citation Rate (diagnostic):** fraction of runs where `bookpinch.com` is cited as a source.

## Output

- `dashboard/` (static HTML + generated `data.json`, no server): Presence heatmap (city × engine)
  as the headline view, emergent competitor leaderboard per city, citation-gap view.
- `docs/` short results report + methodology note, including the limitation below.

## Known Limitation (stated plainly in the report)

API-grounded answers approximate, but do not perfectly equal, what a person sees in the consumer
ChatGPT / Perplexity / Gemini apps. Standard, defensible way to measure GEO at scale, but an
approximation — labeled as such.

## Success Criteria

- One command runs the full pipeline end to end against real keys and populates SQLite, with
  every engine web-grounded.
- Dashboard renders a Presence heatmap (city × engine) plus emergent competitor leaderboards.
- Adding a new expansion city requires editing only `cities.json`.
- Report answers: "In each city, on each engine, how often does an AI name Pinch, and who does it
  name instead?"
