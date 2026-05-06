# Coding Conventions

**Analysis Date:** 2026-05-06

## Naming Patterns

**Files:**
- Modules use lowercase with underscores: `orchestrator.py`, `llms.py`, `parser.py`, `score.py`
- Test files use `test_` prefix: `test_parser.py`, `test_llms.py`
- Script utilities use descriptive lowercase names: `smoke_test.py`, `spot_check.py`

**Functions:**
- Public functions use snake_case: `generate()`, `score_one()`, `run_battery()`, `aggregate()`
- Private/internal functions use leading underscore with snake_case: `_claude()`, `_gpt()`, `_gemini_call()`, `_perplexity()`, `_calc_cost()`, `_compute_geo_()`
- Adapter functions follow pattern `_<provider>()` for LLM providers

**Variables:**
- Local variables use snake_case: `response_text`, `max_tokens`, `model_name`, `total_cost`
- Constants use UPPER_SNAKE_CASE: `DB_PATH`, `PRICING`, `SCHEMA`, `AGGREGATE_SQL`, `W_MENTION`, `W_STRENGTH`, etc.
- Database columns follow snake_case: `run_date`, `query_id`, `response_tokens`, `cost_usd`, `mentioned_rate`

**Types:**
- Type aliases use PascalCase: `ModelName` (defined in `geo/llms.py` as `Literal["claude", "gpt", "gemini", "perplexity"]`)
- Dataclasses use PascalCase: `Response`, `CompetitorScore`, `CellScore`
- Pydantic BaseModel subclasses use PascalCase: `FirecrawlInfo` (in `hello.py`), `ToolMention`, `Mentions`

## Code Style

**Formatting:**
- No explicit linting/formatting tool configured (no .eslintrc, .prettierrc, or pyproject.toml detected)
- Python style follows general PEP 8 conventions
- Indentation: 4 spaces
- String quoting: Double quotes for docstrings, f-strings for interpolation
- Line length: Variable, some lines exceed 80 characters

**Linting:**
- Not detected - no configuration files present

## Import Organization

**Order:**
1. `from __future__ import annotations` (at top of many modules)
2. Standard library imports: `sqlite3`, `json`, `os`, `time`, `pathlib`, `datetime`, `dataclasses`, `math`
3. Third-party imports: `dotenv`, `anthropic`, `openai`, `google.genai`, `pydantic`, `httpx`, `firecrawl`, `typing_extensions`
4. Local imports: `from .llms import ...`, `from .parser import ...`
5. Late imports within functions: `import argparse` (in `__main__` blocks)

**Path Aliases:**
- Relative imports used for local modules: `from .llms import generate, ALL_MODELS, ModelName`
- Root-level imports: `from geo.parser import score_one`, `from geo.llms import generate, ALL_MODELS`

## Error Handling

**Patterns:**
- Broad `except Exception` catches with logging in orchestrator (`geo/orchestrator.py` lines 95-99)
- Specific exception handling for validation errors: `except ValidationError` in `score_one_with_retry()` returns `None`
- Retry logic with exponential backoff: `score_one_with_retry()` implements exponential sleep (1s, 2s, 4s) with configurable `max_attempts`
- API error handling: `r.raise_for_status()` in Perplexity adapter to validate HTTP response
- Silent failures: Some operations log errors but continue (e.g., parser validation errors return `None` rather than propagating)

Example from `geo/parser.py` lines 146-156:
```python
for attempt in range(max_attempts):
    try:
        return score_one(response_text, competitor)
    except ValidationError as e:
        print(f"!! parser validation error for {competitor}: {e}")
        return None
    except Exception as e:
        last_error = e
        wait = 2 ** attempt  # 1s, 2s, 4s
        print(f"!! attempt {attempt+1} failed: {e}"
              f"retruing in {wait}s")
        time.sleep(wait)
```

## Logging

**Framework:** `print()` statements (no logging library like `logging` module)

**Patterns:**
- Console output for progress: `print(f" [{n_done}/{n_total}] {model}/{query['id']}/r{run_idx} ...")`
- Error reporting prefixed with `!!`: `print(f"!! parser validation error for {competitor}: {e}")`
- Summary statistics at end: `print(f"\n[done] {n_done} cells, {n_skipped} skipped, ...")`
- Test output uses descriptive labels: `print(f"\n === Response {label} ===")` in `test_parser.py`

## Comments

**When to Comment:**
- Module docstrings describe purpose: `"""run the full battery, persist results, support resume-from-failure."""`
- Inline comments explain non-obvious decisions: `# in the db? skip it.` (line 84 in orchestrator)
- Comments explain configuration: `# reducing this reduces cost, but you lose some statistical power` (line 58 in orchestrator)
- Section comments separate major blocks: `# 2: persist the response` (line 101 in orchestrator)

**JSDoc/TSDoc:**
- Not used (Python codebase)
- Pydantic `Field()` descriptions provide schema documentation:
```python
mentioned: bool = Field(
    description=(
        "True ONLY if this specific competitor was named or "
        "described unambiguously..."
    )
)
```

## Function Design

**Size:** Functions range from 5 lines (`_calc_cost()`) to 140 lines (`run_battery()`). Most are under 50 lines.

**Parameters:**
- Functions use type hints with modern Python syntax: `def generate(model: ModelName, prompt: str, max_tokens: int = 2000) -> Response`
- Default parameters used sparingly: `max_tokens=400`, `runs_per_cell=2`, `out_path="dashboard/data.json"`
- List type hints use `list[Type]` notation (Python 3.9+): `models: list[ModelName] = None`

**Return Values:**
- Explicit return types: `-> Response`, `-> CompetitorScore`, `-> list[CellScore]`, `-> dict[tuple[str, str, str], dict]`
- Functions return typed dataclass instances or lists: `return Response(...)`, `return [CellScore(...) for ...]`
- Optional returns: `-> Optional[CompetitorScore]` (from `typing`)

## Module Design

**Exports:**
- Modules expose public functions without explicit `__all__` declaration
- Public API: `generate()`, `score_one()`, `score_one_with_retry()`, `run_battery()`, `aggregate()`, `normalize()`
- Constants exported: `ALL_MODELS`, `ModelName`, `PRICING`, `DB_PATH`
- Dataclasses exported: `Response`, `CompetitorScore`, `CellScore`

**Barrel Files:**
- `geo/__init__.py` is empty (no re-exports)
- Imports are explicit: `from geo.llms import ...` or `from .llms import ...`

## Notable Style Issues

**Inconsistencies detected:**
1. String concatenation with `\` for line continuation (SQL queries in `score.py` lines 21-38, 113-140)
2. Inconsistent spacing around operators: `r=_gemini.models.generate_content(` (line 99 in `llms.py`, no space around `=`)
3. Comment typos: `"retruing"` instead of `"retrying"` (line 155 in `parser.py`)
4. Trailing whitespace in docstrings (minor)

---

*Convention analysis: 2026-05-06*
