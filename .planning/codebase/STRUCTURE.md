# Codebase Structure

**Analysis Date:** 2026-05-06

## Directory Layout

```
firecrawl/
├── .env                    # Environment variables (secrets; not committed)
├── .gitignore              # Standard Python ignores
├── .git/                   # Git repository metadata
├── .planning/              # GSD planning documents (auto-created)
├── .venv/                  # Python virtual environment (not committed)
├── README.md               # Project overview, methodology, usage
├── requirements.txt        # Python package dependencies
├── vercel.json             # Deployment config for Vercel (dashboard hosting)
├── queries.json            # Input: 38 queries across 5 intent segments
├── competitors.json        # Input: 6 competitors and their aliases
├── test_queries.json       # Input: 2 sample queries for testing
├── geo/                    # Core measurement system
│   ├── __init__.py         # Package marker (empty)
│   ├── orchestrator.py     # Battery orchestration & CLI
│   ├── llms.py             # LLM provider adapters (4 providers)
│   ├── parser.py           # Firecrawl-based response scoring
│   └── score.py            # Aggregation, GEO formula, export
├── data/                   # Persistent state
│   ├── results.sqlite      # SQLite DB (responses + scores tables)
│   └── spot_check.json     # Manual validation results (reference data)
├── dashboard/              # Web UI (single-page application)
│   ├── index.html          # HTML template with Chart.js charts
│   ├── dashboard.js        # Client-side rendering and interactivity
│   └── data.json           # Generated export from geo/score.py
├── hello.py                # Unused demo file
├── smoke_test.py           # Unused test file
├── spot_check.py           # Manual validation script (queries one response per competitor)
├── test_llms.py            # Unit test for LLM adapters
└── test_parser.py          # Unit test for parser (score_one function)
```

## Directory Purposes

**`geo/`:**
- Purpose: Core measurement pipeline (LLM calls, parsing, aggregation)
- Contains: Python modules for orchestration, adapters, and analysis
- Key files: `orchestrator.py` (entry point), `llms.py` (providers), `parser.py` (scoring), `score.py` (aggregation)

**`data/`:**
- Purpose: Persistent state and reference data
- Contains: SQLite database (auto-created by orchestrator), spot-check results
- Key files: `results.sqlite` (1.3 MB; contains responses and scores tables)

**`dashboard/`:**
- Purpose: Web UI for visualizing GEO rankings and competitive analysis
- Contains: Static HTML/JS and generated JSON data export
- Key files: `index.html` (template), `dashboard.js` (rendering), `data.json` (from score.py)

**`(root)`:**
- Purpose: Configuration, input data, tests, and CLI entry points
- Contains: Requirements, JSON input files, test scripts, deployment config

## Key File Locations

**Entry Points:**
- `geo/orchestrator.py`: Run measurement battery (`python -m geo.orchestrator [args]`)
- `geo/score.py`: Export aggregated scores to dashboard (`python -m geo.score`)
- `dashboard/index.html`: Open in browser or deploy to Vercel

**Configuration:**
- `requirements.txt`: Python dependencies (8 main packages: anthropic, openai, google-genai, firecrawl-py, pydantic, python-dotenv, httpx, perplexity)
- `vercel.json`: Deployment config (serves `dashboard/` as static site)
- `.env`: API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, PERPLEXITY_API_KEY, FIRECRAWL_API_KEY)

**Core Logic:**
- `geo/llms.py`: LLM provider adapters (Anthropic, OpenAI, Google, Perplexity)
- `geo/parser.py`: Firecrawl-based scoring of competitor mentions
- `geo/score.py`: GEO formula computation and dashboard data export
- `geo/orchestrator.py`: Battery coordination, response persistence, resume-from-failure

**Testing:**
- `test_llms.py`: Tests for adapter functions
- `test_parser.py`: Tests for score_one function with hand-crafted responses
- `spot_check.py`: Manual validation script for spot-checking results

**Input Data:**
- `queries.json`: 38 queries across segments (agent_building, rag_ingest, research_monitoring, comparison_shopping, adversarial)
- `competitors.json`: 6 competitors (Firecrawl, Apify, Browserbase, Bright Data, Zyte, ScrapingBee) with name aliases
- `test_queries.json`: 2 queries for testing

## Naming Conventions

**Files:**
- Module files: lowercase with underscore (e.g., `orchestrator.py`, `llms.py`)
- Test files: `test_*.py` (e.g., `test_parser.py`)
- Config files: LOWERCASE.json (e.g., `queries.json`, `competitors.json`)
- Data files: LOWERCASE.sqlite or .json (e.g., `results.sqlite`, `data.json`)

**Directories:**
- Python package: `geo/` (lowercase)
- Data storage: `data/` (lowercase)
- Web assets: `dashboard/` (lowercase)

**Functions:**
- Private/internal: `_function_name()` (leading underscore; e.g., `_claude()`, `_calc_cost()`)
- Public/exported: `function_name()` (e.g., `generate()`, `score_one()`, `aggregate()`)

**Classes/Types:**
- Pydantic models: `CamelCase` (e.g., `CompetitorScore`, `Response`)
- Type aliases: `snake_case_type` (e.g., `ModelName` = Literal["claude", "gpt", ...])
- Dataclasses: `CamelCase` (e.g., `CellScore`)

**Constants:**
- Configuration: UPPERCASE_SNAKE (e.g., `DB_PATH`, `SCHEMA`, `PRICING`, `W_MENTION`, `W_STRENGTH`)

**SQL tables:**
- `responses`: LLM outputs per (run_date, model, query_id, run_index)
- `scores`: Parsed competitor mentions per (response_id, competitor)

## Where to Add New Code

**New Feature (e.g., add a 5th LLM provider):**
- Add adapter function to `geo/llms.py` (pattern: wrap provider SDK, return `Response` dataclass)
- Add entry to `PRICING` dict (line 34-39)
- Add case to `generate()` dispatch (line 160-170)
- Add to `ALL_MODELS` list (line 172)
- Update `ModelName` Literal type (line 19)

**New Metric or Aggregation:**
- Add SQL query to `geo/score.py`
- Add aggregation function (pattern: execute SQL, build result structure, return list/dict)
- Call from `export_dashboard_data()` if public-facing, or from utility function if internal

**New Test:**
- Co-locate with tested module: `test_*.py` in root (e.g., add to `test_parser.py` or `test_llms.py`)
- Pattern: Import test function, call with test data, assert on output

**New Dashboard Feature (e.g., add a chart):**
- Edit `dashboard/index.html` to add canvas element and chart container
- Edit `dashboard/dashboard.js` to instantiate Chart.js instance and render
- If new data needed: add to export in `geo/score.py` → `export_dashboard_data()`

**Utilities or Helpers:**
- Shared helpers for parsing: add to `geo/parser.py`
- Shared helpers for LLM calls: add to `geo/llms.py`
- Shared helpers for scoring: add to `geo/score.py`
- No separate `utils.py`; keep functionality close to usage

## Special Directories

**`.planning/codebase/`:**
- Purpose: GSD analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (created by GSD mapper)
- Committed: Yes (part of planning artifacts)

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (created by `python -m venv .venv`)
- Committed: No (in `.gitignore`)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (created automatically by Python)
- Committed: No (in `.gitignore`)

**`data/results.sqlite`:**
- Purpose: Persistent SQLite database for responses and scores
- Generated: Yes (created by `orchestrator.py` on first run)
- Committed: No (in `.gitignore` or excluded from repo; only checked in if snapshot for reference)

---

*Structure analysis: 2026-05-06*
