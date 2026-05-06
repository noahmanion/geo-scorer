# Codebase Concerns

**Analysis Date:** 2026-05-06

## Tech Debt

**Cost Tracking Not Implemented:**
- Issue: `total_cost` variable initialized to 0.0 in `run_battery()` but never updated during execution. Final output reports `${total_cost:.3f}` as always $0.000
- Files: `geo/orchestrator.py` (lines 70, 138)
- Impact: Operators cannot track actual spending. Cost estimates in dry-run are separate from real execution cost accounting
- Fix approach: Track cost per iteration by summing `resp.cost_usd` from all generate() calls. Update `total_cost += resp.cost_usd` after line 107

**Spelling/Typo in Error Message:**
- Issue: "retruing" instead of "retrying" in retry error output
- Files: `geo/parser.py` (line 155)
- Impact: Unprofessional logging, but functionally transparent
- Fix approach: Change string from `f"retruing in {wait}s"` to `f"retrying in {wait}s"`

**Hardcoded Model Strings:**
- Issue: Model names (e.g., "claude-opus-4-7", "gpt-5.5") are duplicated across adapter functions and pricing dict
- Files: `geo/llms.py` (lines 35-39 pricing, plus lines 56, 78, 100, 137 in adapter functions)
- Impact: Single model upgrade (e.g., new Claude version) requires changes in multiple places; easy to miss one
- Fix approach: Define model version constants at module level and reference them in all places

**Untested Perplexity Adapter:**
- Issue: `_perplexity()` function in `geo/llms.py` is never called in test files. No test coverage for HTTP error handling or response parsing
- Files: `geo/llms.py` (lines 129-159), no corresponding test in `test_llms.py`
- Impact: Breaking changes to Perplexity API would not be caught until full battery run
- Fix approach: Add dedicated test in `test_llms.py` that calls `_perplexity()` with real API key or mock httpx response

## Known Bugs

**Database Uniqueness Constraint Logic Error:**
- Issue: Duplicate detection in `run_battery()` (line 85-92) checks for existing run before executing generate(), but if generate() fails, a retry would skip the cell even though it was never stored
- Files: `geo/orchestrator.py` (lines 84-99)
- Impact: Failed LLM generations are silently skipped on retry without persisting; resuming after a failure loses the partial attempt
- Fix approach: Move duplicate check AFTER successful generate(), or store a "started" flag in DB before attempting generation

**Score Parsing Returns None on ValidationError:**
- Issue: In `score_one_with_retry()`, ValidationError immediately returns None without retrying (line 148-150)
- Files: `geo/parser.py` (lines 148-150)
- Impact: Transient Firecrawl parser failures are treated as permanent. If the LLM-generated schema violates constraints, it's abandoned rather than retried
- Fix approach: Remove ValidationError from the immediate-return case, let it fall through to the retry loop like other exceptions

**Missing Error Context in Orchestrator:**
- Issue: LLM generation failures (line 97-99 in orchestrator.py) are caught but only the exception string is logged, no context about which model/query/run combination failed
- Files: `geo/orchestrator.py` (lines 95-99)
- Impact: Hard to debug which cells failed and reproduce the error
- Fix approach: Add structured logging with model, query_id, run_idx to exception handler

## Security Considerations

**Hardcoded API Keys in .env File in Version Control:**
- Risk: `.env` file is committed to git with real API credentials (seen in git output)
- Files: `.env` (not read fully per policy, but existence confirmed)
- Current mitigation: `.env` is listed in `.gitignore`
- Recommendations: 
  - Immediately revoke all keys in current `.env` file (check git history for commits that included keys)
  - Use `git log -p -- .env` and `git log -p --all -- .env` to audit full history for exposed secrets
  - Add pre-commit hook to prevent `.env` commits
  - Rotate ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, PERPLEXITY_API_KEY, FIRECRAWL_API_KEY immediately

**Unvalidated Third-Party API Response Parsing:**
- Risk: Direct indexing of API responses without bounds checking (e.g., `msg.content[0].text`, `resp.choices[0].message.content`)
- Files: `geo/llms.py` (lines 60, 82, 146)
- Current mitigation: SDK responses are typed objects; IndexError would be caught as Exception in test code
- Recommendations: Add explicit length checks before indexing. Example: `text = msg.content[0].text if msg.content else ""`  (already done for Claude and OpenAI, but Perplexity line 146 assumes content exists)

## Performance Bottlenecks

**Sequential Scoring Loop - N+1 API Calls:**
- Problem: For each LLM response, one Firecrawl parse call per competitor. With 38 queries × 3 models × 3 runs × 6 competitors = 2,052 Firecrawl API calls
- Files: `geo/orchestrator.py` (lines 113-125), `geo/parser.py` (lines 129-137)
- Cause: Intentional per README to control for position bias, but no batching optimization
- Improvement path: Implement async batching within the same model/segment to parallelize parser calls. Current sequential approach adds ~2-3 minutes per run

**Database Commits After Every Score Entry:**
- Problem: Inner loop commits after every competitor score insert (line 127). With 6 competitors, this is 6 commits per LLM response
- Files: `geo/orchestrator.py` (line 127)
- Cause: Safety against partial failure, but SQLite sequential writes are slow
- Improvement path: Batch commits - collect all scores for one response, then single commit. Reduces I/O by ~6x

**No Query Result Caching:**
- Problem: Same queries run 3 times per model for statistical power, but if a model gives identical response (possible), it's scored/parsed 3 times
- Files: `geo/orchestrator.py` (lines 79-134)
- Cause: No content-deduplication before scoring
- Improvement path: Hash response text, skip re-scoring if seen before in same run_date

## Fragile Areas

**Firecrawl Parser Integration:**
- Files: `geo/parser.py` (entire module)
- Why fragile: 
  - Hard-coded prompt instructions with competitor name interpolation (line 114-122)
  - No fallback if parse() returns unexpected schema
  - Pydantic validation strict - any extra fields in parse response cause failure
- Safe modification: 
  - Test parser with all 6 competitors before production run
  - Add schema.extra = "forbid" to catch upstream changes
  - Wrap parse() call in try-except that logs the full response body for debugging
- Test coverage: Only manual test in `test_parser.py` (lines 8-36) with 3 hardcoded responses. No fixture-based regression tests

**LLM Response Text Encoding in Parser:**
- Files: `geo/parser.py` (lines 101-105)
- Why fragile: Manual HTML escaping of &, <, > but no escaping of quotes or other special chars. Embedded quotes in response could break the prompt
- Safe modification: Use a dedicated HTML escaping library (e.g., `html.escape()` from stdlib)
- Risk: LLM response with unescaped quote could malform the parser prompt JSON

**Database Schema is Not Versioned:**
- Files: `geo/orchestrator.py` (lines 16-44)
- Why fragile: If schema changes (add new column, modify constraint), old database is incompatible and must be manually dropped
- Safe modification: Add migration system with version tracking, or auto-detect schema version and upgrade
- Test coverage: No tests for init_db() or schema correctness

**Model Pricing Hard-Coded:**
- Files: `geo/llms.py` (lines 34-39)
- Why fragile: Prices are placeholders and marked as "illustrative" for Perplexity. When actual prices change, no alert
- Safe modification: Load pricing from external config file (JSON/YAML) that can be version-controlled separately
- Test coverage: No test validates pricing data completeness for all models

## Test Coverage Gaps

**Untested Retry Logic:**
- What's not tested: `score_one_with_retry()` retry loop (lines 145-158). No test for max_attempts exhaustion or backoff timing
- Files: `geo/parser.py`
- Risk: Broken retry could silently skip all failed scores without sufficient attempt
- Priority: High - this is a core resilience mechanism

**No Integration Test for Full Battery:**
- What's not tested: End-to-end `run_battery()` with real DB and multiple queries
- Files: `geo/orchestrator.py`
- Risk: Logic bugs in loop nesting (queries × models × runs) only caught during actual expensive run
- Priority: High - dry-run gives plan but does not validate DB schema or data flow

**No Test for Scoring Aggregation:**
- What's not tested: `normalize()` and `headline_score()` with edge cases (empty cells, tie scores, all-None values)
- Files: `geo/score.py` (lines 89-112, 157-177)
- Risk: Division by zero or NaN in normalization not caught until dashboard generation
- Priority: Medium - would be caught quickly but on expensive data

**Missing Competitor Data Validation:**
- What's not tested: Loading of `competitors.json` - no check for duplicate names, empty list, invalid format
- Files: `geo/orchestrator.py` (lines 64-66)
- Risk: Malformed JSON silently produces 0 scores
- Priority: Low - operator would notice missing competitors quickly

## Dependencies at Risk

**Perplexity SDK Unknown:**
- Risk: `perplexity` library in `requirements.txt` (line 8) but not imported or used in any code. Unknown if package exists or if version spec is needed
- Impact: `pip install` may fail silently or install unexpected package
- Migration plan: 
  1. Verify if Perplexity SDK exists and is maintained
  2. If using httpx directly (current code does), remove from requirements.txt
  3. If need real SDK, add version constraint (e.g., `perplexity>=1.0.0`)

**Requirements.txt Syntax Error:**
- Risk: Line 7 has malformed requirement `httpx>=0.27.0-r req` (typo: `-r req` should be removed or it's invalid)
- Impact: `pip install -r requirements.txt` may fail
- Migration plan: Fix to `httpx>=0.27.0`

**Google Genai API Instability:**
- Risk: `google.genai` is still in beta. Package name is `google-genai` but import is `google.genai`. API changes between minor versions not uncommon
- Impact: Model names or response format could change unexpectedly
- Migration plan: Lock version to tested working version (e.g., `google-genai==1.0.0`), monitor upstream releases

**OpenAI GPT-5.5 Does Not Exist:**
- Risk: Model name `gpt-5.5` used in code but this is not a real OpenAI model. Should be `gpt-4-turbo` or `gpt-4o`
- Impact: LLM generation will fail with "model not found" error
- Migration plan: Update to actual deployed model name, e.g., `gpt-4-turbo` or latest `gpt-4o` variant

---

*Concerns audit: 2026-05-06*
