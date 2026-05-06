# Firecrawl GEO Rank Tracker

Measures how Firecrawl is recommended across major LLMs vs competitors.

## Methodology

**Query set.** 38 queries across 5 intent segments: agent-building, RAG
ingest, research/monitoring, comparison/shopping, adversarial. Queries
mirror real developer language. Full set in `queries.json`.

**Models.** Claude Opus 4.7, GPT-5.5, Gemini 2.5 Flash, Perplexity Sonar
Pro. Each query run 3 times per model at temperature 0.7, max_tokens=400
(verbosity control).

**Competitor set.** Firecrawl, Apify, Browserbase, Bright Data, Zyte,
ScrapingBee. Defined in `competitors.json`.

**Parser.** Each LLM response is scored against each competitor by
Firecrawl's structured extraction (one parser call per competitor, to
control for position bias in the judge). Pydantic schema in `geo/parser.py`.

**Rubric.** Four signals per (response, competitor):
- `mentioned`: boolean
- `position`: 1=first named, 2=second, etc
- `strength`: 0=not mentioned, 1=alternative, 2=secondary, 3=primary
- `context_quality`: 0=not mentioned, 1=errors, 2=accurate, 3=current details

**GEO Score.**
```
GEO_Score = (mention_rate × 3.0)
+ (avg_strength_when_mentioned × 2.0)
+ (avg_context_quality_when_mentioned × 1.5)
- (avg_position_when_mentioned × 0.3)
```
Then normalized 0-10 across the matrix.

## Known limitations

- **Sample size.** 456 LLM observations is adequate for top-3 ranking,
not for differentiating minor competitors. Top-3 stable across re-runs;
ranks 4-6 noisier.
- **Recommendation, not conversion.** A high GEO score does not equal
a signup. Pairing with attribution is the natural next step.
- **No agent-loop coverage.** This measures the chat-LLM layer (a developer
asks an LLM what to use). It does NOT measure agent-loop recommendations
(Cursor / Claude Code calling Firecrawl during code generation).
See `ch10_agent_loop.md` for a sketch of how to instrument that.
- **Self-enhancement bias.** Firecrawl's structured extraction is the
parser. Cross-model judging would be more rigorous; the current setup
is an acceptable trade-off for v1.

## Scoring Methodology

This section mirrors `docs/scoring-methodology.pdf` for users browsing the
repo on the web. Regenerate both with `python3 scripts/generate_docs.py`.

### Overview

The PoC measures how four major LLMs recommend Firecrawl versus five
competitors when answering developer-intent queries. Output: a 0-10 GEO
score per (model, segment, competitor) cell, plus an overall headline
score per competitor.

### Process

1. Run a 38-query battery across 5 intent segments against Claude Opus 4.7,
   GPT-5.5, Gemini 2.5 Flash, and Perplexity Sonar Pro. Each query runs 3
   times per model at temperature 0.7.
2. For every (response, competitor) pair, call Firecrawl's structured
   extraction parser ONCE -- one parser call per competitor, never batched,
   to control for position bias in the judge.
3. Persist responses and per-competitor scores in SQLite
   (`data/results.sqlite`), with UNIQUE constraints enabling
   resume-from-failure.
4. Aggregate to GEO scores and normalize to 0-10 (see formula below).
5. Export `dashboard/data.json` for the static dashboard.

### Rubric

Each (response, competitor) parser call produces four signals:

- `mentioned` -- boolean. True only if the competitor is named or
  unambiguously described. Generic mentions of "web scraping APIs" do
  not count.
- `position` -- 1 = first named, 2 = second, etc. First mention only.
- `strength` -- 0=not mentioned, 1=competing alternative, 2=secondary
  recommendation, 3=primary recommendation.
- `context_quality` -- 0=not mentioned, 1=factual errors, 2=accurate
  general info, 3=accurate with current details (correct API surface,
  recent features, accurate pricing).

### GEO Score formula

```
GEO_raw = (mention_rate              x 3.0)
        + (avg_strength_when_mentioned x 2.0)
        + (avg_context_quality_when_mentioned x 1.5)
        - (avg_position_when_mentioned x 0.3)
```

Then linearly normalized 0-10 across the entire (model x segment x
competitor) matrix: max observed -> 10, min observed -> 0. Weights are
defined in `geo/score.py` (`W_MENTION`, `W_STRENGTH`, `W_CONTEXT`,
`W_POSITION`) and are configurable for sensitivity analysis.

### Quality Assurance

- **Spot-check audit.** A sample of 30 parser scores were reviewed by a
  human against the underlying LLM response text. 27/30 (90%) agreed.
  All 3 disagreements were parser false positives (claimed a mention
  that the human reviewer judged absent); 2 of the 3 were on GPT
  responses. Source: `data/spot_check.json`.
- **One-call-per-competitor.** Each parser call evaluates exactly one
  competitor, eliminating position bias inside the judge.
- **Resume-from-failure.** SQLite UNIQUE constraints make orchestrator
  re-runs idempotent; failed cells can be repopulated without
  duplicating data.

### Known Limitations

- **Sample size.** ~456 LLM observations is adequate for top-3 ranking,
  not for differentiating minor competitors. Top-3 is stable across
  re-runs; ranks 4-6 are noisier.
- **Recommendation, not conversion.** A high GEO score does not equal a
  signup. Pairing with attribution is the natural next step.
- **No agent-loop coverage.** This measures the chat-LLM layer (a
  developer asks an LLM what to use). It does NOT measure agent-loop
  recommendations (Cursor / Claude Code calling Firecrawl during code
  generation).
- **Self-enhancement bias.** Firecrawl's structured extraction is the
  parser. Cross-model judging would be more rigorous; the current setup
  is an acceptable trade-off for v1.
- **Known data gap.** GPT and several Gemini cells in the current
  `dashboard/data.json` show all zeros due to a `max_tokens=400`
  truncation issue. The fix (`max_tokens=2000`) is in code; a re-run is
  pending to repopulate those cells.

## Reproducing

```bash
git clone <this repo>
cp .env.example .env # add your API keys
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m geo.orchestrator --dry-run # check plan
python -m geo.orchestrator # run battery (~90 min, ~$60)
python -m geo.score # export dashboard data
cd dashboard && python -m http.server 8000
```
