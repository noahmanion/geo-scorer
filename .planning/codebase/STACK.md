# Technology Stack

**Analysis Date:** 2026-05-06

## Languages

**Primary:**
- Python 3.13 - Main implementation language for all backend code

## Runtime

**Environment:**
- Python 3.13.1 - Runtime environment specified in `.venv`
- Virtual environment: `.venv` (present, using Python 3.13)

**Package Manager:**
- pip - Standard Python package manager
- Lockfile: `requirements.txt` (pinned versions present)

## Frameworks

**Core:**
- Pydantic 2.0+ - Data validation and structured extraction schemas (`geo/parser.py`)

**HTTP/API:**
- httpx 0.27.0+ - Async HTTP client for Perplexity API calls (`geo/llms.py:130`)
- python-dotenv 1.0+ - Environment variable management (`geo/llms.py:9`)

**Testing/Utilities:**
- No formal testing framework detected (ad-hoc test files: `test_llms.py`, `test_parser.py`, `smoke_test.py`)

**Build/Deployment:**
- Vercel - Static hosting for dashboard frontend (configured in `vercel.json`)

## Key Dependencies

**Critical:**
- Anthropic SDK (anthropic>=0.97.0) - Claude API integration (`geo/llms.py:11`, `geo/llms.py:52-68`)
- OpenAI SDK (openai>=2.0.0) - GPT API integration (`geo/llms.py:74-90`)
- Google GenAI SDK (google-genai>=1.0.0) - Gemini API integration (`geo/llms.py:96-123`)
- Firecrawl SDK (firecrawl-py>=2.0.0) - Structured extraction and parsing (`geo/parser.py:13-14`, `geo/orchestrator.py:107-124`)

**Infrastructure:**
- Perplexity HTTP API - Accessed directly via httpx (no SDK) (`geo/llms.py:129-159`)

## Configuration

**Environment:**
- Configured via `.env` file (created from `.env.example` per README)
- Environment variables required:
  - `ANTHROPIC_API_KEY` - Claude API key (auto-loaded by Anthropic SDK)
  - `OPENAI_API_KEY` - GPT API key (auto-loaded by OpenAI SDK)
  - `GEMINI_API_KEY` - Gemini API key (explicit: `geo/llms.py:96`)
  - `PERPLEXITY_API_KEY` - Perplexity API key (explicit: `geo/llms.py:134`)
  - `FIRECRAWL_API_KEY` - Firecrawl API key (explicit: `geo/parser.py:90`)

**Build:**
- Vercel static hosting configuration: `vercel.json` (routes dashboard to static HTML)

## Database

**SQLite:**
- Local SQLite database at `data/results.sqlite` (`geo/orchestrator.py:14`)
- Schema defined in `geo/orchestrator.py:16-44` with two tables:
  - `responses` - LLM query results and token counts
  - `scores` - Parsed competitor mention scoring

## Platform Requirements

**Development:**
- Python 3.13
- Virtual environment (`.venv`)
- Git (repository managed in `.git`)

**Production:**
- Vercel static hosting (dashboard only - `dashboard/` directory)
- API keys for: Anthropic, OpenAI, Google GenAI, Perplexity, Firecrawl

## Architecture Notes

- **Modular design:** Each LLM provider has dedicated adapter function (`_claude()`, `_gpt()`, `_gemini_call()`, `_perplexity()`) in `geo/llms.py`
- **Structured extraction:** Pydantic schema (`CompetitorScore` in `geo/parser.py:22-88`) enforces output format for Firecrawl parsing
- **Cost tracking:** All API calls include token count and USD cost computation (`geo/llms.py:41-45`)

---

*Stack analysis: 2026-05-06*
