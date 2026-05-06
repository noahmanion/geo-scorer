<!-- GSD:project-start source:PROJECT.md -->
## Project

**Firecrawl GEO Intelligence PoC**

An internal intelligence tool that measures how Firecrawl is recommended across major LLMs versus its competitors. It runs a battery of developer-intent queries against Claude, GPT, Gemini, and Perplexity, scores each response for competitor mentions (presence, position, strength, and accuracy), and surfaces results through a static dashboard deployed on Vercel.

**Core Value:** Know where Firecrawl stands in LLM recommendations across query segments — and have the data infrastructure to track it over time.

### Constraints

- **Tech**: Python 3.13, SQLite (no cloud DB), static frontend only — no backend server
- **Cost**: LLM costs ~$0.22 for test battery (15 queries); Firecrawl parse credits ~4.37 credits/call
- **Scope**: Internal Firecrawl use only — no auth, no multi-tenancy
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.13 - Main implementation language for all backend code
## Runtime
- Python 3.13.1 - Runtime environment specified in `.venv`
- Virtual environment: `.venv` (present, using Python 3.13)
- pip - Standard Python package manager
- Lockfile: `requirements.txt` (pinned versions present)
## Frameworks
- Pydantic 2.0+ - Data validation and structured extraction schemas (`geo/parser.py`)
- httpx 0.27.0+ - Async HTTP client for Perplexity API calls (`geo/llms.py:130`)
- python-dotenv 1.0+ - Environment variable management (`geo/llms.py:9`)
- No formal testing framework detected (ad-hoc test files: `test_llms.py`, `test_parser.py`, `smoke_test.py`)
- Vercel - Static hosting for dashboard frontend (configured in `vercel.json`)
## Key Dependencies
- Anthropic SDK (anthropic>=0.97.0) - Claude API integration (`geo/llms.py:11`, `geo/llms.py:52-68`)
- OpenAI SDK (openai>=2.0.0) - GPT API integration (`geo/llms.py:74-90`)
- Google GenAI SDK (google-genai>=1.0.0) - Gemini API integration (`geo/llms.py:96-123`)
- Firecrawl SDK (firecrawl-py>=2.0.0) - Structured extraction and parsing (`geo/parser.py:13-14`, `geo/orchestrator.py:107-124`)
- Perplexity HTTP API - Accessed directly via httpx (no SDK) (`geo/llms.py:129-159`)
## Configuration
- Configured via `.env` file (created from `.env.example` per README)
- Environment variables required:
- Vercel static hosting configuration: `vercel.json` (routes dashboard to static HTML)
## Database
- Local SQLite database at `data/results.sqlite` (`geo/orchestrator.py:14`)
- Schema defined in `geo/orchestrator.py:16-44` with two tables:
## Platform Requirements
- Python 3.13
- Virtual environment (`.venv`)
- Git (repository managed in `.git`)
- Vercel static hosting (dashboard only - `dashboard/` directory)
- API keys for: Anthropic, OpenAI, Google GenAI, Perplexity, Firecrawl
## Architecture Notes
- **Modular design:** Each LLM provider has dedicated adapter function (`_claude()`, `_gpt()`, `_gemini_call()`, `_perplexity()`) in `geo/llms.py`
- **Structured extraction:** Pydantic schema (`CompetitorScore` in `geo/parser.py:22-88`) enforces output format for Firecrawl parsing
- **Cost tracking:** All API calls include token count and USD cost computation (`geo/llms.py:41-45`)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Modules use lowercase with underscores: `orchestrator.py`, `llms.py`, `parser.py`, `score.py`
- Test files use `test_` prefix: `test_parser.py`, `test_llms.py`
- Script utilities use descriptive lowercase names: `smoke_test.py`, `spot_check.py`
- Public functions use snake_case: `generate()`, `score_one()`, `run_battery()`, `aggregate()`
- Private/internal functions use leading underscore with snake_case: `_claude()`, `_gpt()`, `_gemini_call()`, `_perplexity()`, `_calc_cost()`, `_compute_geo_()`
- Adapter functions follow pattern `_<provider>()` for LLM providers
- Local variables use snake_case: `response_text`, `max_tokens`, `model_name`, `total_cost`
- Constants use UPPER_SNAKE_CASE: `DB_PATH`, `PRICING`, `SCHEMA`, `AGGREGATE_SQL`, `W_MENTION`, `W_STRENGTH`, etc.
- Database columns follow snake_case: `run_date`, `query_id`, `response_tokens`, `cost_usd`, `mentioned_rate`
- Type aliases use PascalCase: `ModelName` (defined in `geo/llms.py` as `Literal["claude", "gpt", "gemini", "perplexity"]`)
- Dataclasses use PascalCase: `Response`, `CompetitorScore`, `CellScore`
- Pydantic BaseModel subclasses use PascalCase: `FirecrawlInfo` (in `hello.py`), `ToolMention`, `Mentions`
## Code Style
- No explicit linting/formatting tool configured (no .eslintrc, .prettierrc, or pyproject.toml detected)
- Python style follows general PEP 8 conventions
- Indentation: 4 spaces
- String quoting: Double quotes for docstrings, f-strings for interpolation
- Line length: Variable, some lines exceed 80 characters
- Not detected - no configuration files present
## Import Organization
- Relative imports used for local modules: `from .llms import generate, ALL_MODELS, ModelName`
- Root-level imports: `from geo.parser import score_one`, `from geo.llms import generate, ALL_MODELS`
## Error Handling
- Broad `except Exception` catches with logging in orchestrator (`geo/orchestrator.py` lines 95-99)
- Specific exception handling for validation errors: `except ValidationError` in `score_one_with_retry()` returns `None`
- Retry logic with exponential backoff: `score_one_with_retry()` implements exponential sleep (1s, 2s, 4s) with configurable `max_attempts`
- API error handling: `r.raise_for_status()` in Perplexity adapter to validate HTTP response
- Silent failures: Some operations log errors but continue (e.g., parser validation errors return `None` rather than propagating)
## Logging
- Console output for progress: `print(f" [{n_done}/{n_total}] {model}/{query['id']}/r{run_idx} ...")`
- Error reporting prefixed with `!!`: `print(f"!! parser validation error for {competitor}: {e}")`
- Summary statistics at end: `print(f"\n[done] {n_done} cells, {n_skipped} skipped, ...")`
- Test output uses descriptive labels: `print(f"\n === Response {label} ===")` in `test_parser.py`
## Comments
- Module docstrings describe purpose: `"""run the full battery, persist results, support resume-from-failure."""`
- Inline comments explain non-obvious decisions: `# in the db? skip it.` (line 84 in orchestrator)
- Comments explain configuration: `# reducing this reduces cost, but you lose some statistical power` (line 58 in orchestrator)
- Section comments separate major blocks: `# 2: persist the response` (line 101 in orchestrator)
- Not used (Python codebase)
- Pydantic `Field()` descriptions provide schema documentation:
## Function Design
- Functions use type hints with modern Python syntax: `def generate(model: ModelName, prompt: str, max_tokens: int = 2000) -> Response`
- Default parameters used sparingly: `max_tokens=400`, `runs_per_cell=2`, `out_path="dashboard/data.json"`
- List type hints use `list[Type]` notation (Python 3.9+): `models: list[ModelName] = None`
- Explicit return types: `-> Response`, `-> CompetitorScore`, `-> list[CellScore]`, `-> dict[tuple[str, str, str], dict]`
- Functions return typed dataclass instances or lists: `return Response(...)`, `return [CellScore(...) for ...]`
- Optional returns: `-> Optional[CompetitorScore]` (from `typing`)
## Module Design
- Modules expose public functions without explicit `__all__` declaration
- Public API: `generate()`, `score_one()`, `score_one_with_retry()`, `run_battery()`, `aggregate()`, `normalize()`
- Constants exported: `ALL_MODELS`, `ModelName`, `PRICING`, `DB_PATH`
- Dataclasses exported: `Response`, `CompetitorScore`, `CellScore`
- `geo/__init__.py` is empty (no re-exports)
- Imports are explicit: `from geo.llms import ...` or `from .llms import ...`
## Notable Style Issues
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
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
- **Stateless adapters:** Each LLM provider is wrapped identically; swapping models requires only string changes
- **Structured extraction, not LLM judging:** Competitor mentions scored by Firecrawl's parser, not by a separate judge LLM (eliminates cascading bias)
- **One-call-per-competitor pattern:** Parser invoked per (response, competitor) pair to control for position bias in evaluation
- **Deterministic scoring:** GEO formula is deterministic math on aggregated signals, normalized 0-10 for interpretation
## Layers
- Purpose: Coordinate measurement battery; invoke LLMs on queries; persist results
- Location: `geo/orchestrator.py`
- Contains: `run_battery()` function, CLI arg parsing, dry-run mode
- Depends on: `llms.generate()`, `parser.score_one_with_retry()`, `sqlite3`
- Used by: Root orchestrator (CLI entry point), test harness
- Purpose: Normalize calls to four external LLM providers into a single `Response` dataclass
- Location: `geo/llms.py`
- Contains: Provider-specific wrapper functions (_claude, _gpt, _gemini_call, _perplexity), pricing config, cost calculation
- Depends on: Anthropic SDK, OpenAI SDK, Google GenAI SDK, httpx (for Perplexity), dotenv
- Used by: `orchestrator.py` via `generate()` dispatch function
- Purpose: Use Firecrawl's structured extraction to score competitor mentions in LLM responses
- Location: `geo/parser.py`
- Contains: `CompetitorScore` Pydantic schema, `score_one()` with retry logic, Firecrawl integration
- Depends on: Firecrawl SDK, Pydantic for validation
- Used by: `orchestrator.py` for each competitor in each response
- Purpose: Store LLM responses and parsed scores; support deduplication and resume-from-failure
- Location: `data/results.sqlite` (auto-created)
- Schema: Two main tables (`responses`, `scores`), three indexes
- Used by: `orchestrator.py` for writes, `score.py` for aggregation reads
- Purpose: Compute GEO scores from raw signals; normalize; prepare export for dashboard
- Location: `geo/score.py`
- Contains: SQL aggregation queries, GEO formula implementation, stddev calculation, JSON export
- Depends on: sqlite3, dataclasses, JSON serialization
- Used by: Score export script (CLI entry point), dashboard data prep
- Purpose: Visualize GEO rankings and competitive breakdown
- Location: `dashboard/`
- Contains: Single-page HTML with Chart.js visualization, static JS for rendering
- Data source: `dashboard/data.json` (generated by `geo/score.py`)
- Deployment: Vercel (configured in `vercel.json`)
## Data Flow
### Primary Request Path: Measurement Battery
### Secondary Flow: Score Aggregation & Export
### Tertiary Flow: LLM Response Parsing
- LLM responses persisted to SQLite on success (line 108 in orchestrator)
- Scores written per-competitor in same transaction (lines 117-125)
- No in-memory state across calls; all recovery via DB queries
## Key Abstractions
- Purpose: Normalize LLM output across providers (Anthropic, OpenAI, Google, Perplexity)
- Defined in: `geo/llms.py` lines 22-30
- Fields: model (string), text (response content), input_tokens, output_tokens, cost_usd, raw (SDK response for debugging)
- Used by: Each adapter function returns one; orchestrator writes to DB
- Purpose: Structured evaluation of a single competitor's presence in one LLM response
- Defined in: `geo/parser.py` lines 22-87
- Fields: mentioned (bool), position (1-indexed order), strength (0-3 scale), context_quality (0-3 scale), confidence (0-1), evidence_quote (verbatim text)
- Used by: Firecrawl parser as schema target, then written to scores table
- Purpose: Aggregated metrics for one (model, segment, competitor) combination
- Defined in: `geo/score.py` lines 40-50
- Contains: raw counts (n_obs, mention_rate) and computed GEO score
- Produced by: `aggregate()`, then `normalize()`
- Purpose: Type-safe enumeration of supported LLM providers
- Defined in: `geo/llms.py` line 19
- Values: "claude", "gpt", "gemini", "perplexity"
- Used by: CLI args, dispatch in `generate()`, PRICING lookup
## Entry Points
- Location: `geo/orchestrator.py` lines 142-178
- Triggers: `python -m geo.orchestrator [--queries] [--competitors] [--runs] [--models] [--dry-run]`
- Responsibilities: Parse args, run `run_battery()` or print dry-run plan
- Default args: queries="queries.json", competitors="competitors.json", runs=3
- Location: `geo/score.py` lines 216-217
- Triggers: `python -m geo.score`
- Responsibilities: Call `export_dashboard_data()` to write `dashboard/data.json`
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
- **LLM generation errors:** Caught at orchestrator (line 95-99). On error, print message and `continue` to next cell. Cell is skipped; no fallback retry in orchestrator (relies on operator to re-run battery for failed cells).
- **Parser validation errors:** `score_one_with_retry()` catches `ValidationError` and returns `None` (line 148-150). Score row not inserted if competitor parse fails.
- **Parser transient errors:** Exponential backoff (1s, 2s, 4s) with up to 3 attempts. If all fail, print error and return `None` (line 157-158). Cell incomplete but not fatal.
- **Database errors:** Not caught; fail-fast (UNIQUE constraint, FK violations will raise and halt orchestrator). This is intentional to avoid silent data corruption.
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
