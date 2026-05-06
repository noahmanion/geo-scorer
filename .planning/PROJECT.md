# Firecrawl GEO Intelligence PoC

## What This Is

An internal intelligence tool that measures how Firecrawl is recommended across major LLMs versus its competitors. It runs a battery of developer-intent queries against Claude, GPT, Gemini, and Perplexity, scores each response for competitor mentions (presence, position, strength, and accuracy), and surfaces results through a static dashboard deployed on Vercel.

## Core Value

Know where Firecrawl stands in LLM recommendations across query segments — and have the data infrastructure to track it over time.

## Requirements

### Validated

- ✓ Query battery runs against 4 LLMs (Claude, GPT, Gemini, Perplexity) — Phase 0
- ✓ Responses persisted to SQLite with resume-from-failure support — Phase 0
- ✓ Firecrawl structured extraction grades each response per competitor — Phase 0
- ✓ GEO scoring formula (mention rate × 3.0, strength × 2.0, context × 1.5, position × −0.3) — Phase 0
- ✓ Scores normalized 0–10 across matrix — Phase 0
- ✓ Static dashboard (ranking chart + segment breakdown) deployed on Vercel — Phase 0
- ✓ Spot-check audit tool for manual parser validation — Phase 0

### Active

(PoC complete — no active requirements)

### Out of Scope

- Multi-brand / self-serve product — internal use only for now
- Real-time or scheduled automated runs — manual execution via CLI
- Agent-loop coverage (Cursor/Claude Code recommendations) — different measurement layer
- Attribution or conversion tracking — GEO score ≠ signup signal

## Context

Built following the "Building a GEO Rank Tracker" field guide. Key implementation details from this session:

- **Query set**: 38 queries across 5 intent segments (agent-building, RAG ingest, research/monitoring, comparison/shopping, adversarial) in `queries.json`
- **Competitor set**: Firecrawl, Apify, Browserbase, Bright Data, Zyte, ScrapingBee — defined in `competitors.json`
- **Parser**: Firecrawl's `/parse` endpoint with a Pydantic `CompetitorScore` schema; one call per (response, competitor) to avoid position bias
- **DB**: SQLite at `data/results.sqlite` with UNIQUE constraint on `(run_date, model, query_id, run_index)` enabling idempotent re-runs
- **Dashboard**: Pure static site (`dashboard/`) served via Vercel with `vercel.json` routing
- **Known data quality issue**: GPT-5.5 and Gemini 2.5 Flash are reasoning models — `max_tokens=400` is consumed by internal thinking, producing empty/truncated responses. Fixed in `llms.py` (bumped to `max_tokens=2000`); existing bad rows deleted, re-run pending

## Constraints

- **Tech**: Python 3.13, SQLite (no cloud DB), static frontend only — no backend server
- **Cost**: LLM costs ~$0.22 for test battery (15 queries); Firecrawl parse credits ~4.37 credits/call
- **Scope**: Internal Firecrawl use only — no auth, no multi-tenancy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Firecrawl as LLM-as-judge parser | Uses `data:` URL trick to parse arbitrary text; structured extraction via Pydantic schema | ✓ Good — 90% spot-check agreement |
| One parser call per competitor | Avoids position bias in the judge when scoring multiple competitors | ✓ Good |
| SQLite over cloud DB | Simplicity for PoC; resume-from-failure via UNIQUE constraint | ✓ Good |
| Static dashboard on Vercel | No server needed; `dashboard/data.json` committed and served directly | ✓ Good |
| `max_tokens=2000` for reasoning models | GPT-5.5 and Gemini 2.5 Flash burn token budget on internal reasoning before visible output | — Pending re-run to validate |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-06 after initialization*
