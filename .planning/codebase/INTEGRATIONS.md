# External Integrations

**Analysis Date:** 2026-05-06

## APIs & External Services

**LLM Providers:**
- Claude (Anthropic) - Primary LLM for generating responses
  - SDK: `anthropic>=0.97.0`
  - Auth: `ANTHROPIC_API_KEY` (env var)
  - Model: `claude-opus-4-7` (`geo/llms.py:56`)
  - Implementation: `geo/llms.py:52-68` (`_claude()` function)

- GPT (OpenAI) - Alternative LLM provider
  - SDK: `openai>=2.0.0`
  - Auth: `OPENAI_API_KEY` (env var)
  - Model: `gpt-5.5` (`geo/llms.py:78`)
  - Implementation: `geo/llms.py:74-90` (`_gpt()` function)

- Gemini (Google) - Alternative LLM provider
  - SDK: `google-genai>=1.0.0`
  - Auth: `GEMINI_API_KEY` (env var, explicit)
  - Model: `gemini-2.5-flash` (`geo/llms.py:100`)
  - Implementation: `geo/llms.py:96-123` (`_gemini_call()` function)

- Perplexity - Alternative LLM provider (Sonar model)
  - HTTP API: `https://api.perplexity.ai/chat/completions` (`geo/llms.py:130`)
  - Auth: `PERPLEXITY_API_KEY` (Bearer token in header)
  - Model: `sonar-pro` (`geo/llms.py:137`)
  - Client: httpx (no SDK) (`geo/llms.py:130-159` directly over HTTP)

**Structured Extraction:**
- Firecrawl - Web scraping and structured extraction service
  - SDK: `firecrawl-py>=2.0.0`
  - Auth: `FIRECRAWL_API_KEY` (env var)
  - Implementation: `geo/parser.py:90` (initialization), `geo/parser.py:107-126` (parse call)
  - Usage: Parses LLM responses into typed Pydantic schema (`CompetitorScore`)
  - Schema format: JSON extraction with custom prompt (`geo/parser.py:111-123`)

## Data Storage

**Databases:**
- SQLite (local file)
  - Connection: `data/results.sqlite` (file path)
  - Usage: Persistent storage for experiment results
  - Client: Python standard `sqlite3` module
  - Tables:
    - `responses` - Stores LLM outputs, token counts, costs (`geo/orchestrator.py:17-28`)
    - `scores` - Stores parsed competitor mention scores (`geo/orchestrator.py:30-41`)

**File Storage:**
- Local filesystem only
  - Query sets: `queries.json`, `test_queries.json`
  - Competitor config: `competitors.json`
  - Results: `data/results.sqlite`
  - Dashboard data: `dashboard/data.json` (generated)

**Caching:**
- None detected

## Authentication & Identity

**Auth Providers:**
- Custom (API key-based)
  - Each external service authenticated via individual API keys in `.env`
  - Keys loaded via `python-dotenv` (`geo/llms.py:9`, `geo/parser.py:15`)

**Auth Pattern:**
- Environment variables (standard pattern)
- Anthropic/OpenAI/Google SDKs auto-detect `*_API_KEY` vars
- Perplexity uses explicit header: `Authorization: Bearer {PERPLEXITY_API_KEY}` (`geo/llms.py:134`)
- Firecrawl uses explicit initialization: `Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])` (`geo/parser.py:90`)

## Monitoring & Observability

**Error Tracking:**
- None configured

**Logs:**
- Print statements to stdout (ad-hoc logging)
- Progress tracking in `geo/orchestrator.py:132-134` (cell completion, cost, ETA)
- Error reporting in `geo/parser.py:149-158` (retry attempts logged)

## CI/CD & Deployment

**Hosting:**
- Vercel - Static hosting for dashboard frontend
  - Config: `vercel.json` (routes `/` to `/dashboard/index.html`)
  - Deployment path: `/dashboard` directory

**API Calls:**
- No backend API hosted - orchestrator runs locally
- All API calls made from client environment (development/local execution)

## Environment Configuration

**Required env vars:**
1. `ANTHROPIC_API_KEY` - Claude API key (Anthropic)
2. `OPENAI_API_KEY` - GPT API key (OpenAI)
3. `GEMINI_API_KEY` - Gemini API key (Google)
4. `PERPLEXITY_API_KEY` - Perplexity API key
5. `FIRECRAWL_API_KEY` - Firecrawl API key

**Setup:**
- Copy `.env.example` to `.env` and populate with actual keys (per README)
- Keys are loaded via `python-dotenv` at module initialization

**Secrets location:**
- `.env` file (local, not committed to git - listed in `.gitignore`)

## Data Flow

**Main Workflow (Orchestrator):**
1. Load queries from `queries.json`
2. Load competitor list from `competitors.json`
3. For each (query, model, run_index) combination:
   - Call LLM via `geo.llms.generate()` (hits API)
   - Store response + token counts in SQLite
   - For each competitor:
     - Call Firecrawl parser on response text
     - Score competitor mention via structured extraction
     - Store score in SQLite

**Scoring Workflow:**
1. Query SQLite for all responses and scores
2. Aggregate by (model, segment, competitor) via SQL
3. Compute GEO score using formula (`geo/score.py:52-64`)
4. Normalize across matrix (0-10 scale) (`geo/score.py:89-112`)
5. Export aggregated results to `dashboard/data.json`

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

---

*Integration audit: 2026-05-06*
