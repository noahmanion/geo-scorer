<!-- refreshed: 2026-05-06 -->
# Architecture

**Analysis Date:** 2026-05-06

## System Overview

This is a measurement system that quantifies how Firecrawl is recommended by large language models across different query contexts and competitors. The system orchestrates LLM calls, parses responses using Firecrawl's structured extraction, aggregates scores, and visualizes rankings.

```text
┌─────────────────────────────────────────────────────────────┐
│                 Query Execution Layer                        │
│           Orchestrates LLM generation runs                   │
│  `geo/orchestrator.py`: run_battery(), init_db()             │
└────────────┬──────────────────────────────────┬─────────────┘
             │                                  │
             ▼                                  ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│  LLM Adapter Layer           │  │  Parser & Scoring Layer      │
│  `geo/llms.py`               │  │  `geo/parser.py`             │
│  - _claude()                 │  │  - score_one()               │
│  - _gpt()                    │  │  - score_one_with_retry()    │
│  - _gemini_call()            │  │  - CompetitorScore schema    │
│  - _perplexity()             │  │                              │
│  - generate()                │  └──────────────┬───────────────┘
│  - Response dataclass        │                 │
└──────────────┬───────────────┘                 │
               │                                  │
               ▼                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  SQLite Persistence Layer                                    │
│  `data/results.sqlite`                                       │
│  - responses table (LLM outputs)                             │
│  - scores table (competitor scores)                          │
└────────────┬──────────────────────────────────┬──────────────┘
             │                                  │
             └──────────────┬───────────────────┘
                            ▼
        ┌─────────────────────────────────────┐
        │   Aggregation & Analysis Layer      │
        │   `geo/score.py`                    │
        │   - aggregate()                     │
        │   - normalize()                     │
        │   - stddevs()                       │
        │   - export_dashboard_data()         │
        └──────────────────┬────────────────┘
                           ▼
        ┌─────────────────────────────────────┐
        │   Presentation Layer                │
        │   `dashboard/` (HTML/JS)            │
        │   - index.html                      │
        │   - dashboard.js                    │
        │   - data.json (export from score.py)│
        └─────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Orchestrator | Manage measurement battery lifecycle: init DB, iterate queries×models×runs, persist responses | `geo/orchestrator.py` |
| LLM Adapters | Abstract four LLM providers (Anthropic, OpenAI, Google, Perplexity) behind unified `Response` | `geo/llms.py` |
| Parser | Score each (response, competitor) pair using Firecrawl's structured extraction with retry logic | `geo/parser.py` |
| Scorer | Aggregate raw scores by (model, segment, competitor), compute GEO metric, normalize 0-10 | `geo/score.py` |
| Database | Persist responses and scores; support resume-from-failure via uniqueness constraints | `data/results.sqlite` |
| Dashboard | Visualize GEO rankings, competitive performance by segment, render headline score | `dashboard/` |

## Pattern Overview

**Overall:** Three-tier pipeline with SQL-backed persistence and resume capability.

**Key Characteristics:**
- **Stateless adapters:** Each LLM provider is wrapped identically; swapping models requires only string changes
- **Structured extraction, not LLM judging:** Competitor mentions scored by Firecrawl's parser, not by a separate judge LLM (eliminates cascading bias)
- **One-call-per-competitor pattern:** Parser invoked per (response, competitor) pair to control for position bias in evaluation
- **Deterministic scoring:** GEO formula is deterministic math on aggregated signals, normalized 0-10 for interpretation

## Layers

**Orchestrator Layer:**
- Purpose: Coordinate measurement battery; invoke LLMs on queries; persist results
- Location: `geo/orchestrator.py`
- Contains: `run_battery()` function, CLI arg parsing, dry-run mode
- Depends on: `llms.generate()`, `parser.score_one_with_retry()`, `sqlite3`
- Used by: Root orchestrator (CLI entry point), test harness

**LLM Adapter Layer:**
- Purpose: Normalize calls to four external LLM providers into a single `Response` dataclass
- Location: `geo/llms.py`
- Contains: Provider-specific wrapper functions (_claude, _gpt, _gemini_call, _perplexity), pricing config, cost calculation
- Depends on: Anthropic SDK, OpenAI SDK, Google GenAI SDK, httpx (for Perplexity), dotenv
- Used by: `orchestrator.py` via `generate()` dispatch function

**Parser & Scoring Layer:**
- Purpose: Use Firecrawl's structured extraction to score competitor mentions in LLM responses
- Location: `geo/parser.py`
- Contains: `CompetitorScore` Pydantic schema, `score_one()` with retry logic, Firecrawl integration
- Depends on: Firecrawl SDK, Pydantic for validation
- Used by: `orchestrator.py` for each competitor in each response

**Persistence Layer:**
- Purpose: Store LLM responses and parsed scores; support deduplication and resume-from-failure
- Location: `data/results.sqlite` (auto-created)
- Schema: Two main tables (`responses`, `scores`), three indexes
- Used by: `orchestrator.py` for writes, `score.py` for aggregation reads

**Aggregation & Analysis Layer:**
- Purpose: Compute GEO scores from raw signals; normalize; prepare export for dashboard
- Location: `geo/score.py`
- Contains: SQL aggregation queries, GEO formula implementation, stddev calculation, JSON export
- Depends on: sqlite3, dataclasses, JSON serialization
- Used by: Score export script (CLI entry point), dashboard data prep

**Presentation Layer:**
- Purpose: Visualize GEO rankings and competitive breakdown
- Location: `dashboard/`
- Contains: Single-page HTML with Chart.js visualization, static JS for rendering
- Data source: `dashboard/data.json` (generated by `geo/score.py`)
- Deployment: Vercel (configured in `vercel.json`)

## Data Flow

### Primary Request Path: Measurement Battery

1. **Init** (`orchestrator.py` lines 47-52): `init_db()` creates schema if missing
2. **Load inputs** (`orchestrator.py` lines 64-66): Read `queries.json` and `competitors.json`
3. **Iterate cells** (`orchestrator.py` lines 79-127): For each (query, model, run_index):
   - Skip if already in DB (resume-from-failure check, line 85-92)
   - Call LLM via `generate()` dispatch → get `Response` with cost (line 96)
   - Insert response to `responses` table (lines 102-110)
   - For each competitor, score via `score_one_with_retry()` (lines 113-125)
   - Insert scores to `scores` table with foreign key back to response (lines 117-125)
   - Commit after each competitor (line 127)
4. **Progress reporting** (`orchestrator.py` lines 129-134): Print ETA and cumulative cost

**Resume capability:** Each (run_date, model, query_id, run_index) tuple is unique; if present, row is skipped (line 85-92).

### Secondary Flow: Score Aggregation & Export

1. **Aggregate** (`score.py` lines 66-87): Run `AGGREGATE_SQL` to group by (model, segment, competitor)
   - Compute: mention_rate, avg_strength, avg_context, avg_position
2. **Normalize** (`score.py` lines 89-112): Linear scale GEO scores 0-10 across entire matrix
3. **Stddev** (`score.py` lines 142-155): Calculate per-cell variance for error bars
4. **Headlines** (`score.py` lines 157-184): Compute weighted score per competitor across all cells
5. **Export** (`score.py` lines 186-214): Dump to `dashboard/data.json` with all three tiers

### Tertiary Flow: LLM Response Parsing

1. **Escape HTML** (`parser.py` lines 101-104): Sanitize response text to prevent injection
2. **Wrap as HTML** (`parser.py` lines 105): Embed in `<pre>` for Firecrawl consumption
3. **Call Firecrawl** (`parser.py` lines 107-124): Invoke parser with `CompetitorScore` schema + prompt
4. **Retry on error** (`parser.py` lines 139-158): Exponential backoff (1s, 2s, 4s), catch ValidationError, return None if exhausted

**State Management:**
- LLM responses persisted to SQLite on success (line 108 in orchestrator)
- Scores written per-competitor in same transaction (lines 117-125)
- No in-memory state across calls; all recovery via DB queries

## Key Abstractions

**Response (Dataclass):**
- Purpose: Normalize LLM output across providers (Anthropic, OpenAI, Google, Perplexity)
- Defined in: `geo/llms.py` lines 22-30
- Fields: model (string), text (response content), input_tokens, output_tokens, cost_usd, raw (SDK response for debugging)
- Used by: Each adapter function returns one; orchestrator writes to DB

**CompetitorScore (Pydantic BaseModel):**
- Purpose: Structured evaluation of a single competitor's presence in one LLM response
- Defined in: `geo/parser.py` lines 22-87
- Fields: mentioned (bool), position (1-indexed order), strength (0-3 scale), context_quality (0-3 scale), confidence (0-1), evidence_quote (verbatim text)
- Used by: Firecrawl parser as schema target, then written to scores table

**CellScore (Dataclass):**
- Purpose: Aggregated metrics for one (model, segment, competitor) combination
- Defined in: `geo/score.py` lines 40-50
- Contains: raw counts (n_obs, mention_rate) and computed GEO score
- Produced by: `aggregate()`, then `normalize()`

**ModelName (Literal type):**
- Purpose: Type-safe enumeration of supported LLM providers
- Defined in: `geo/llms.py` line 19
- Values: "claude", "gpt", "gemini", "perplexity"
- Used by: CLI args, dispatch in `generate()`, PRICING lookup

## Entry Points

**orchestrator.py (CLI):**
- Location: `geo/orchestrator.py` lines 142-178
- Triggers: `python -m geo.orchestrator [--queries] [--competitors] [--runs] [--models] [--dry-run]`
- Responsibilities: Parse args, run `run_battery()` or print dry-run plan
- Default args: queries="queries.json", competitors="competitors.json", runs=3

**score.py (CLI):**
- Location: `geo/score.py` lines 216-217
- Triggers: `python -m geo.score`
- Responsibilities: Call `export_dashboard_data()` to write `dashboard/data.json`

**dashboard (Web):**
- Location: `dashboard/index.html` + `dashboard/dashboard.js`
- Triggers: HTTP request to `/` or deployed Vercel URL
- Data source: `dashboard/data.json`

## Architectural Constraints

- **Threading:** Single-threaded event loop per Python process. No thread pooling. Sequential LLM calls (i.e., for 3 runs × 4 models × 38 queries, total ~90 min wall-clock assuming ~2s per LLM call).
- **Global state:** Module-level singletons: `_anthropic` (Anthropic client), `_openai` (OpenAI client), `_gemini` (Google client) in `llms.py` lines 52, 74, 96. Initialized once at module load via SDK constructors.
- **Database:** SQLite single file at `data/results.sqlite`. No concurrent writes enforced at DB level; Python GIL and sequential orchestration loop prevent multi-process collisions in practice.
- **Circular imports:** None detected. Module dependency DAG: orchestrator → llms + parser, parser → (external), score → (external), dashboard → (external).
- **Cost ceiling:** Estimated per-battery run ~$60 USD (parameterized by PRICING dict in `llms.py` lines 34-39).

## Error Handling

**Strategy:** Graceful degradation with per-cell failure tolerance.

**Patterns:**
- **LLM generation errors:** Caught at orchestrator (line 95-99). On error, print message and `continue` to next cell. Cell is skipped; no fallback retry in orchestrator (relies on operator to re-run battery for failed cells).
- **Parser validation errors:** `score_one_with_retry()` catches `ValidationError` and returns `None` (line 148-150). Score row not inserted if competitor parse fails.
- **Parser transient errors:** Exponential backoff (1s, 2s, 4s) with up to 3 attempts. If all fail, print error and return `None` (line 157-158). Cell incomplete but not fatal.
- **Database errors:** Not caught; fail-fast (UNIQUE constraint, FK violations will raise and halt orchestrator). This is intentional to avoid silent data corruption.

## Cross-Cutting Concerns

**Logging:** Print-based. Orchestrator logs cell progress (line 132-134); parser logs retry attempts (line 154-156); no structured logging framework.

**Validation:** Pydantic enforces `CompetitorScore` schema (field descriptions, types, ranges). LLM responses are raw strings (no schema validation until parser invocation).

**Authentication:** Env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, PERPLEXITY_API_KEY, FIRECRAWL_API_KEY) loaded via `dotenv` in `llms.py` line 17 and `parser.py` line 19.

---

*Architecture analysis: 2026-05-06*
