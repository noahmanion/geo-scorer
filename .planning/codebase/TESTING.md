# Testing Patterns

**Analysis Date:** 2026-05-06

## Test Framework

**Runner:**
- No formal test framework detected (pytest, unittest, nose not configured)
- Tests are run as standalone Python scripts via `python script.py`

**Assertion Library:**
- No assertion library used
- Manual verification and print-based inspection

**Run Commands:**
```bash
python test_llms.py              # Test LLM adapters
python test_parser.py            # Test parser with sample responses
python smoke_test.py             # Integration smoke test
python spot_check.py             # Interactive audit of parser results
```

## Test File Organization

**Location:**
- Test files in root directory alongside utility scripts (not in separate `tests/` directory)
- No co-location pattern; tests are separate from source code in `geo/` package

**Naming:**
- Pattern: `test_*.py` for unit/integration tests
- Utility scripts: `smoke_test.py`, `spot_check.py` (not named `test_` but serve similar purpose)

**Structure:**
```
firecrawl/
├── test_llms.py              # Tests LLM adapter interface
├── test_parser.py            # Tests parser scoring
├── smoke_test.py             # Tests basic connectivity
├── spot_check.py             # Interactive audit tool
└── geo/
    ├── llms.py               # Implementation
    ├── parser.py             # Implementation
    └── orchestrator.py       # Implementation
```

## Test Structure

**Suite Organization:**
Tests are organized as imperative scripts rather than declarative test cases. Each test file uses a simple pattern:

From `test_llms.py`:
```python
"""
test_llms.py - verify the unified interface works for all 4 models.
"""

from geo.llms import generate, ALL_MODELS

PROMPT = (
    "I'm building an agent thatneeds to fetch and parse arbitrary "
    "websites at runtime. What API should i use to convert page "
    "into clean markdown for context?"
)

total_cost = 0.0
for model in ALL_MODELS:
    try:
        r = generate(model, PROMPT, max_tokens=200)
        print(f"\n=== {model.upper()} ====")
        print(f" tokens: {r.input_tokens} in, {r.output_tokens} out")
        print(f" cost: ${r.cost_usd:.4f}")
        print(f" text: {r.text[:200]}...")
        total_cost += r.cost_usd
    except Exception as e:
        print(f"\n=== {model.upper()}: FAILED ===")
        print(f" {type(e).__name__}: {e}")

print(f"\nTOTAL COST: ${total_cost:.4f}")
```

**Patterns:**
- Loop-based iteration over test cases (`for model in ALL_MODELS`)
- Exception handling for failure detection (`try/except Exception`)
- Print-based verification (no assertions)
- Inline test data (PROMPT constant defined in test file)

## Test Scope

**Smoke Tests:**
`smoke_test.py` - Tests basic API connectivity for all providers:
```python
def test_anthropic():
    from anthropic import Anthropic
    client = Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=20,
        messages=[{"role": "user", "content": "Say 'pong' and stop"}]
    )
    print("anthropic", msg.content[0].text)
```

**Parser Tests:**
`test_parser.py` - Tests scoring logic with three response scenarios:
- `response_a`: Clear primary recommendation (Firecrawl recommended strongly)
- `response_b`: Secondary mention (Firecrawl mentioned but not primary)
- `response_c`: Not mentioned (Firecrawl absent from response)

Calls `score_one()` on each and prints results for manual inspection:
```python
for label, resp in [("A", response_a), ("B", response_b), ("C", response_c)]:
    score = score_one(resp, "firecrawl")
    print(f"\n === Response {label} ===")
    print(f" mentioned: {score.mentioned}")
    print(f" position: {score.position}")
    print(f" strength: {score.strength}")
    print(f" context_quality: {score.context_quality}")
    print(f" confidence: {score.confidence:.2f}")
    print(f" evidence_quote: {score.evidence_quote!r}")
```

## Mocking

**Framework:** No mocking library (no `unittest.mock`, `pytest-mock`, or similar)

**Patterns:**
- Live API calls (tests require real API keys in `.env`)
- No test doubles or fixtures
- External dependencies called directly in tests

## Fixtures and Factories

**Test Data:**
- Inline constants: `PROMPT`, `response_a`, `response_b`, `response_c` defined in test files
- Sample responses as multi-line strings in test files
- No factory pattern or fixture system

**Location:**
- Test data embedded directly in test files
- Production data in `queries.json` and `competitors.json`

## Coverage

**Requirements:** None enforced - no coverage configuration detected

**View Coverage:**
- Not applicable (no test framework to measure coverage)

## Manual Audit Tool

`spot_check.py` - Interactive tool for auditing parser results:
- Pulls 30 random (response, score) pairs from SQLite database
- Displays parser output to human for verification
- Records human judgment: agree/disagree/skip
- Outputs results to `data/spot_check.json`

Example interaction pattern:
```python
verdict = input("\nAgree? [y/n/s=skip]: ").strip().lower()
if verdict == "s":
    continue
notes = ""
if verdict == "n":
    notes = input("What's wrong? ").strip()

results.append({
    "score_id": row["sid"],
    "competitor": row["competitor"],
    "model": row["model"],
    "agree": verdict == "y",
    "notes": notes,
})
```

## Integration Testing

**Approach:** Full end-to-end testing via orchestrator and database

`geo/orchestrator.py` - Main integration test harness:
1. Loads queries and competitors from JSON files
2. Calls `generate()` for each (query, model) pair
3. Persists responses to SQLite
4. Calls `score_one_with_retry()` for each (response, competitor) pair
5. Persists scores to SQLite
6. Supports resume-from-failure via UNIQUE constraint on responses table

Includes `--dry-run` mode for testing plan without API costs:
```python
if args.dry_run:
    queries = json.loads(Path(args.queries).read_text())
    competitors = json.loads(Path(args.competitors).read_text())
    models = args.models or ALL_MODELS
    n_cells = len(queries) * len(models) * args.runs
    n_scores = n_cells * len(competitors)
    print(f"DRY RUN")
    print(f" queries: {len(queries)}")
    print(f" models: {len(models)}")
    print(f" runs/cell: {args.runs}")
    print(f" competitors: {len(competitors)}")
    print(f" total cells: {n_cells}")
    print(f" total scores: {n_scores}")
    print(f" est cost: LLM ${n_cells * 0.005:.2f}, "
          f"FC ${n_scores * 0.02:.2f}")
else:
    run_battery(...)
```

## Error Handling in Tests

**Patterns:**

1. Broad exception catching with logging:
```python
try:
    r = generate(model, PROMPT, max_tokens=200)
    # ... success path
except Exception as e:
    print(f"\n=== {model.upper()}: FAILED ===")
    print(f" {type(e).__name__}: {e}")
```

2. Retry logic in parser test harness:
```python
def score_one_with_retry(
        response_text: str,
        competitor: str,
        max_attempts: int = 3,
) -> Optional[CompetitorScore]:
    last_error = None
    for attempt in range(max_attempts):
        try:
            return score_one(response_text, competitor)
        except ValidationError as e:
            print(f"!! parser validation error for {competitor}: {e}")
            return None
        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(f"!! attempt {attempt+1} failed: {e}"
                  f"retruing in {wait}s")
            time.sleep(wait)
    print(f"!! all attempts failed for {competitor}: {last_error}")
    return None
```

3. Continue-on-error in orchestrator:
```python
try:
    resp = generate(model, query["query"], max_tokens=2000)
except Exception as e:
    print(f" [{n_done}/{n_total}] {model}/{query['id']}/r{run_idx}" f" GENERATE FAILED: {e}")
    continue
```

## Testing Gaps

**Untested areas:**
- `geo/score.py` module has no tests (aggregate, normalize, headline_score functions untested)
- Database initialization logic not tested
- SQL query correctness assumed (complex aggregate and stddev queries in score.py)
- No unit tests for individual helper functions (_calc_cost, _compute_geo_)
- Error handling paths not systematically tested
- Type validation not tested (Pydantic validation only verified in parser)

**Impact:** Bug-prone areas are score aggregation and statistical calculations in `geo/score.py`.

---

*Testing analysis: 2026-05-06*
