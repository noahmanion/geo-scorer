# Pinch GEO Re-Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-target the existing Firecrawl GEO rank tracker to measure how often AI engines name **Pinch** (an at-home med spa) when asked local aesthetics questions, across cities and engines, with web-grounded models and emergent competitor discovery.

**Architecture:** Reuse the existing pipeline shape (LLM clients → SQLite → Firecrawl `/parse` judge → scoring → static dashboard). Change four things: (1) add live web search to the Claude/GPT/Gemini adapters and capture citations; (2) replace the flat dev-query set with city-parameterized consumer queries; (3) invert the parser from "score a known competitor" to "extract every provider named + is Pinch among them"; (4) re-headline scoring on Presence Rate and rework the dashboard to a city×engine heatmap.

**Tech Stack:** Python 3.13, SQLite, `anthropic`, `openai`, `google-genai`, `httpx` (Perplexity), `firecrawl-py`, `pydantic`, `python-dotenv`, `pytest` (new, dev-only). Static HTML/JS dashboard (Chart.js) on Vercel.

## Global Constraints

- **Tracked brand:** Pinch — domain `bookpinch.com`; aliases `pinch`, `bookpinch`, `pinchmed`. `pinchmed.com` 301-redirects to `bookpinch.com`.
- **Cities (v1):** Chicago, Phoenix, Denver, Seattle, Washington DC. Adding a city must require editing only `cities.json`.
- **Engines:** claude, gpt, gemini, perplexity — **all web-grounded**. Perplexity `sonar-pro` is already grounded.
- **Repetitions:** default 3 runs per (city × query × engine) cell.
- **Headline metric:** Presence Rate (per-answer yes/no that Pinch is named, averaged per city and engine). Rank, share-of-voice, citation rate are diagnostics only — do NOT resurrect the normalized 0–10 composite as the headline.
- **Emergent competitors:** never hard-code a competitor list. Competitors are whatever providers each answer names.
- **No new infra:** local SQLite only, static dashboard, manual CLI run. No scheduler, auth, or server.
- **Keys** live in `.env`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `PERPLEXITY_API_KEY`, `FIRECRAWL_API_KEY`.

---

## File Structure

- `cities.json` — **new** — flat list of city objects `{ "name": "Chicago", "state": "IL" }`.
- `queries.json` — **rewrite** — city-templated consumer queries with `{city}` placeholder.
- `brand.json` — **new** — tracked brand config (name, aliases, domain). Replaces `competitors.json` for targeting.
- `competitors.json` — **delete** — superseded by emergent discovery + `brand.json`.
- `geo/config.py` — **new** — pure loaders + cell expansion (cities × queries → concrete prompts); brand alias/domain matching helpers.
- `geo/llms.py` — **modify** — web grounding for claude/gpt/gemini; add `citations: list[str]` to `Response`; update pricing comments.
- `geo/parser.py` — **modify** — add `ProviderExtraction` model + `extract_providers()` + retry wrapper; keep old `CompetitorScore`/`score_one` untouched but unused.
- `geo/orchestrator.py` — **modify** — city dimension in the run matrix and schema; store citations; call `extract_providers`; persist emergent providers + Pinch presence + citation match.
- `geo/score.py` — **rewrite** — Presence Rate per (city, engine), emergent competitor leaderboard per city, share-of-voice, citation rate; export `dashboard/data.json`.
- `dashboard/index.html`, `dashboard/dashboard.js` — **rework** — city×engine presence heatmap, competitor leaderboard, citation-gap view.
- `requirements.txt` — **fix** — repair malformed lines, add `pytest`.
- `tests/` — **new** — `test_config.py`, `test_scoring.py`, `test_brand_match.py` (pytest).
- `README.md`, `docs/scoring-methodology` — **update** — new methodology + limitation.

---

## Task 0: Environment repair and test harness

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`, `pytest.ini`

- [ ] **Step 1: Fix `requirements.txt`**

Replace the whole file with:

```
anthropic>=0.97.0
openai>=2.0.0
google-genai>=1.0.0
firecrawl-py>=2.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.27.0
pytest>=8.0.0
```

(The old file had a corrupt `httpx>=0.27.0-r req` line and a stray `perplexity` package that does not exist — Perplexity is called over raw HTTP via `httpx`.)

- [ ] **Step 2: Install**

Run: `source .venv/bin/activate && pip install -r requirements.txt`
Expected: installs cleanly, `pytest --version` works.

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file).

- [ ] **Step 5: Confirm keys present**

Run: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print([k for k in ['ANTHROPIC_API_KEY','OPENAI_API_KEY','GEMINI_API_KEY','PERPLEXITY_API_KEY','FIRECRAWL_API_KEY'] if os.getenv(k)])"`
Expected: all 5 key names printed. If any missing, stop and tell the user.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini tests/__init__.py
git commit -m "chore: repair requirements, add pytest harness"
```

---

## Task 1: Config — cities, queries, brand, and cell expansion

**Files:**
- Create: `cities.json`, `brand.json`, `geo/config.py`
- Rewrite: `queries.json`
- Delete: `competitors.json`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `geo.config.load_cities(path="cities.json") -> list[dict]` — each `{"name": str, "state": str}`.
  - `geo.config.load_queries(path="queries.json") -> list[dict]` — each `{"id": str, "segment": str, "template": str}`.
  - `geo.config.load_brand(path="brand.json") -> dict` — `{"name": str, "aliases": list[str], "domain": str}`.
  - `geo.config.expand_cells(cities, queries) -> list[dict]` — each `{"city": str, "state": str, "query_id": str, "segment": str, "prompt": str}` where `prompt` = template with `{city}` replaced by `"{name}, {state}"`.

- [ ] **Step 1: Write `cities.json`**

```json
[
  { "name": "Chicago", "state": "IL" },
  { "name": "Phoenix", "state": "AZ" },
  { "name": "Denver", "state": "CO" },
  { "name": "Seattle", "state": "WA" },
  { "name": "Washington", "state": "DC" }
]
```

- [ ] **Step 2: Write `brand.json`**

```json
{
  "name": "Pinch",
  "aliases": ["pinch", "bookpinch", "pinchmed", "pinch med spa", "book pinch"],
  "domain": "bookpinch.com"
}
```

- [ ] **Step 3: Rewrite `queries.json`** (city-templated consumer queries)

```json
[
  { "id": "disc_001", "segment": "discovery", "template": "Who offers at-home or mobile Botox in {city}?" },
  { "id": "disc_002", "segment": "discovery", "template": "Is there a med spa that comes to your house in {city}? Who are the options?" },
  { "id": "intent_001", "segment": "category_intent", "template": "I want Botox but I don't want to go into a clinic in {city}. What are my options for getting it done at home?" },
  { "id": "svc_001", "segment": "service_specific", "template": "Where can I get at-home dermal fillers in {city}?" },
  { "id": "svc_002", "segment": "service_specific", "template": "Who does mobile microneedling or facials at home in {city}?" },
  { "id": "occ_001", "segment": "occasion", "template": "I want to host a Botox party in {city}. Who can send a nurse injector to my home?" },
  { "id": "brand_001", "segment": "brand_aware", "template": "Is Pinch (bookpinch.com), the at-home med spa in {city}, legit? What do reviews say?" }
]
```

- [ ] **Step 4: Delete `competitors.json`**

Run: `git rm competitors.json`

- [ ] **Step 5: Write the failing test** — `tests/test_config.py`

```python
from geo import config


def test_expand_cells_substitutes_city_and_state():
    cities = [{"name": "Chicago", "state": "IL"}]
    queries = [{"id": "disc_001", "segment": "discovery",
                "template": "Who offers at-home Botox in {city}?"}]
    cells = config.expand_cells(cities, queries)
    assert len(cells) == 1
    cell = cells[0]
    assert cell["city"] == "Chicago"
    assert cell["state"] == "IL"
    assert cell["query_id"] == "disc_001"
    assert cell["segment"] == "discovery"
    assert cell["prompt"] == "Who offers at-home Botox in Chicago, IL?"


def test_expand_cells_is_full_cross_product():
    cities = [{"name": "Chicago", "state": "IL"},
              {"name": "Denver", "state": "CO"}]
    queries = [{"id": "a", "segment": "s", "template": "x {city}"},
               {"id": "b", "segment": "s", "template": "y {city}"}]
    assert len(config.expand_cells(cities, queries)) == 4


def test_real_config_files_load_and_expand():
    cities = config.load_cities()
    queries = config.load_queries()
    brand = config.load_brand()
    assert brand["name"] == "Pinch"
    assert "bookpinch" in brand["aliases"]
    cells = config.expand_cells(cities, queries)
    assert len(cells) == len(cities) * len(queries)
    assert all("{city}" not in c["prompt"] for c in cells)
```

- [ ] **Step 6: Run test, verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: geo.config` / `AttributeError`.

- [ ] **Step 7: Implement `geo/config.py`**

```python
"""Pure config loaders and cell expansion for the Pinch GEO run."""
from __future__ import annotations
import json
from pathlib import Path


def load_cities(path: str = "cities.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def load_queries(path: str = "queries.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def load_brand(path: str = "brand.json") -> dict:
    return json.loads(Path(path).read_text())


def expand_cells(cities: list[dict], queries: list[dict]) -> list[dict]:
    """Cross cities × queries into concrete prompts.

    `{city}` in a template is replaced with "Name, ST".
    """
    cells: list[dict] = []
    for city in cities:
        label = f"{city['name']}, {city['state']}"
        for q in queries:
            cells.append({
                "city": city["name"],
                "state": city["state"],
                "query_id": q["id"],
                "segment": q["segment"],
                "prompt": q["template"].replace("{city}", label),
            })
    return cells
```

- [ ] **Step 8: Run test, verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 9: Commit**

```bash
git add cities.json brand.json queries.json geo/config.py tests/test_config.py
git rm --cached competitors.json 2>/dev/null; git add -A
git commit -m "feat: city-templated Pinch query config + cell expansion"
```

---

## Task 2: Brand + citation matching helpers

**Files:**
- Modify: `geo/config.py`
- Test: `tests/test_brand_match.py`

**Interfaces:**
- Produces:
  - `geo.config.brand_domain_cited(domain: str, citations: list[str]) -> bool` — true if `domain` (e.g. `bookpinch.com`) appears as the host of any citation URL, case-insensitive, ignoring `www.` and subpaths.

- [ ] **Step 1: Write the failing test** — `tests/test_brand_match.py`

```python
from geo import config


def test_domain_cited_matches_host_ignoring_www_and_path():
    cites = ["https://www.bookpinch.com/chicago", "https://yelp.com/biz/x"]
    assert config.brand_domain_cited("bookpinch.com", cites) is True


def test_domain_cited_false_when_absent():
    cites = ["https://yelp.com/biz/x", "https://groupon.com/y"]
    assert config.brand_domain_cited("bookpinch.com", cites) is False


def test_domain_cited_handles_pinchmed_redirect_domain():
    cites = ["http://pinchmed.com/"]
    assert config.brand_domain_cited("pinchmed.com", cites) is True


def test_domain_cited_empty_list():
    assert config.brand_domain_cited("bookpinch.com", []) is False
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/test_brand_match.py -v`
Expected: FAIL — `AttributeError: brand_domain_cited`.

- [ ] **Step 3: Implement in `geo/config.py`** (append)

```python
from urllib.parse import urlparse


def brand_domain_cited(domain: str, citations: list[str]) -> bool:
    """True if `domain` is the host of any citation URL.

    Ignores a leading `www.`, is case-insensitive, and ignores path.
    """
    target = domain.lower().removeprefix("www.")
    for url in citations or []:
        host = (urlparse(url).netloc or "").lower().removeprefix("www.")
        if host == target:
            return True
    return False
```

- [ ] **Step 4: Run test, verify it passes**

Run: `pytest tests/test_brand_match.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add geo/config.py tests/test_brand_match.py
git commit -m "feat: citation domain-match helper for brand presence"
```

---

## Task 3: Web-grounded LLM adapters with citations

**Files:**
- Modify: `geo/llms.py`

**Interfaces:**
- Produces: updated `geo.llms.Response` dataclass with a new field `citations: list[str]` (source URLs the engine used; empty list if none). `geo.llms.generate(model, prompt, max_tokens=2000) -> Response` unchanged in signature; every adapter now performs web-grounded generation and populates `citations`.

> **Note on testing:** Web-grounded calls hit live APIs, so these steps use **integration smoke checks** rather than unit tests — mocking each SDK's web-search surface would test the mock, not the grounding. The check asserts a real answer came back and (where the provider exposes them) that citations were captured.

- [ ] **Step 1: Add `citations` to the `Response` dataclass**

In `geo/llms.py`, update the dataclass:

```python
@dataclass
class Response:
    model: ModelName
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    citations: list[str]  # source URLs used by web grounding; [] if none
    raw: object
```

- [ ] **Step 2: Ground the Claude adapter**

Replace `_claude` with:

```python
def _claude(prompt: str, max_tokens: int = 2000) -> Response:
    msg = _anthropic.messages.create(
        model="claude-opus-4-7",
        max_tokens=max_tokens,
        tools=[{"type": "web_search_20250305", "name": "web_search",
                "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
    )
    # Concatenate all text blocks; collect citation URLs from them.
    text_parts, citations = [], []
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
            for cit in (getattr(block, "citations", None) or []):
                url = getattr(cit, "url", None)
                if url:
                    citations.append(url)
    return Response(
        model="claude",
        text="".join(text_parts),
        input_tokens=msg.usage.input_tokens,
        output_tokens=msg.usage.output_tokens,
        cost_usd=_calc_cost("claude", msg.usage.input_tokens,
                            msg.usage.output_tokens),
        citations=list(dict.fromkeys(citations)),
        raw=msg,
    )
```

- [ ] **Step 3: Ground the OpenAI adapter (Responses API + web_search)**

Replace `_gpt` with:

```python
def _gpt(prompt: str, max_tokens: int = 2000) -> Response:
    resp = _openai.responses.create(
        model="gpt-5.5",
        tools=[{"type": "web_search"}],
        max_output_tokens=max_tokens,
        input=prompt,
    )
    text = resp.output_text or ""
    citations = []
    for item in (resp.output or []):
        for content in (getattr(item, "content", None) or []):
            for ann in (getattr(content, "annotations", None) or []):
                url = getattr(ann, "url", None)
                if url:
                    citations.append(url)
    usage = resp.usage
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    return Response(
        model="gpt",
        text=text,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=_calc_cost("gpt", in_tok, out_tok),
        citations=list(dict.fromkeys(citations)),
        raw=resp,
    )
```

- [ ] **Step 4: Ground the Gemini adapter (google_search grounding)**

Replace `_gemini_call` with:

```python
def _gemini_call(prompt: str, max_tokens: int = 2000) -> Response:
    resp = _gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
            tools=[genai_types.Tool(
                google_search=genai_types.GoogleSearch())],
        ),
    )
    text = resp.text or ""
    citations = []
    for cand in (resp.candidates or []):
        meta = getattr(cand, "grounding_metadata", None)
        for chunk in (getattr(meta, "grounding_chunks", None) or []):
            web = getattr(chunk, "web", None)
            url = getattr(web, "uri", None)
            if url:
                citations.append(url)
    usage = resp.usage_metadata
    return Response(
        model="gemini",
        text=text,
        input_tokens=usage.prompt_token_count or 0,
        output_tokens=usage.candidates_token_count or 0,
        cost_usd=_calc_cost("gemini", usage.prompt_token_count or 0,
                            usage.candidates_token_count or 0),
        citations=list(dict.fromkeys(citations)),
        raw=resp,
    )
```

- [ ] **Step 5: Capture Perplexity citations**

Replace the tail of `_perplexity` (after `data = r.json()`) with:

```python
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    citations = data.get("citations") or [
        s.get("url") for s in data.get("search_results", []) if s.get("url")
    ]
    return Response(
        model="perplexity",
        text=text,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        cost_usd=_calc_cost("perplexity", usage.get("prompt_tokens", 0),
                            usage.get("completion_tokens", 0)),
        citations=[c for c in citations if c],
        raw=data,
    )
```

- [ ] **Step 6: Integration smoke check — all four engines return grounded local answers**

Create a throwaway check (do not commit it): `scratch_grounding.py`

```python
from geo.llms import generate, ALL_MODELS

prompt = "Who offers at-home or mobile Botox in Chicago, IL? Name specific providers."
for m in ALL_MODELS:
    r = generate(m, prompt)
    print(f"\n=== {m} ===")
    print("text[:300]:", r.text[:300].replace("\n", " "))
    print("n_citations:", len(r.citations), r.citations[:3])
    assert r.text.strip(), f"{m} returned empty text"
```

Run: `python scratch_grounding.py`
Expected: each engine prints a non-empty answer naming real Chicago-area providers. Perplexity, GPT, and Gemini should show ≥1 citation; Claude usually shows citations when it searched. If an SDK signature differs from the code above (web-search tool shapes evolve), fix the adapter until this passes, then delete `scratch_grounding.py`.

- [ ] **Step 7: Commit**

```bash
git add geo/llms.py
git commit -m "feat: web-grounded LLM adapters that capture citations"
```

---

## Task 4: Emergent provider extraction in the parser

**Files:**
- Modify: `geo/parser.py`

**Interfaces:**
- Consumes: `geo.config.load_brand()` for alias matching context (passed in by caller).
- Produces:
  - `geo.parser.ProviderExtraction` (pydantic): `providers: list[ProviderMention]`, `pinch_present: bool`, `pinch_position: Optional[int]`, `evidence_quote: str`.
  - `geo.parser.ProviderMention` (pydantic): `name: str`, `position: int`.
  - `geo.parser.extract_providers(response_text: str, brand_aliases: list[str]) -> ProviderExtraction`
  - `geo.parser.extract_with_retry(response_text: str, brand_aliases: list[str], max_attempts: int = 3) -> Optional[ProviderExtraction]`

> **Testing note:** `extract_providers` calls Firecrawl live, so verification is an integration smoke check (Step 5). The pydantic models and the retry-wrapper control flow are the pure parts; the retry wrapper mirrors the existing `score_one_with_retry` exactly.

- [ ] **Step 1: Add the pydantic models to `geo/parser.py`** (below `CompetitorScore`)

```python
class ProviderMention(BaseModel):
    name: str = Field(description="Name of one business/provider the "
                      "response names as an option for the user.")
    position: int = Field(description="1 = first named, 2 = second, etc. "
                          "Order of first appearance in the response.")


class ProviderExtraction(BaseModel):
    """Every provider an LLM answer names, plus whether Pinch is among them."""
    providers: list[ProviderMention] = Field(
        default_factory=list,
        description="All distinct businesses/providers named as options, "
                    "in the order first mentioned. Exclude generic advice "
                    "('ask a dermatologist') and non-providers.")
    pinch_present: bool = Field(
        description="True ONLY if Pinch (aka bookpinch / pinchmed / "
                    "'Pinch Med Spa') is named or unambiguously described. "
                    "Be strict.")
    pinch_position: Optional[int] = Field(
        None, description="Pinch's position among named providers "
                          "(1=first). Null if not present.")
    evidence_quote: str = Field(
        description="Exact sentence naming Pinch, for auditing. Empty "
                    "string if not present.")
```

- [ ] **Step 2: Add `extract_providers`** to `geo/parser.py`

```python
def extract_providers(response_text: str,
                      brand_aliases: list[str]) -> ProviderExtraction:
    """Extract every provider an answer names + whether Pinch is present.

    One Firecrawl parser call over the response text.
    """
    safe = (response_text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
    html_bytes = f"<html><body><pre>{safe}</pre></body></html>".encode()
    alias_str = ", ".join(brand_aliases)

    result = _app.parse(
        html_bytes,
        filename="response.html",
        content_type="text/html",
        options=ScrapeOptions(formats=[{
            "type": "json",
            "schema": ProviderExtraction.model_json_schema(),
            "prompt": (
                "This page contains an AI assistant's answer to a consumer "
                "asking who provides at-home aesthetic/med-spa services in a "
                "city. Extract EVERY specific business or provider the answer "
                "names as an option, in order of first mention. Exclude "
                "generic advice and non-providers. Then decide whether the "
                f"brand 'Pinch' is among them — treat any of these as Pinch: "
                f"{alias_str}. Be strict: only mark pinch_present if it is "
                "clearly named. Provide an exact evidence_quote naming Pinch."
            )
        }]),
    )
    return ProviderExtraction(**result.json)


def extract_with_retry(response_text: str, brand_aliases: list[str],
                       max_attempts: int = 3) -> Optional[ProviderExtraction]:
    last_error = None
    for attempt in range(max_attempts):
        try:
            return extract_providers(response_text, brand_aliases)
        except ValidationError as e:
            print(f"!! extraction validation error: {e}")
            return None
        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(f"!! attempt {attempt+1} failed: {e}; retrying in {wait}s")
            time.sleep(wait)
    print(f"!! all extraction attempts failed: {last_error}")
    return None
```

- [ ] **Step 3: Integration smoke check** — create throwaway `scratch_extract.py` (do not commit)

```python
from geo.parser import extract_providers

resp = ("For at-home Botox in Chicago you have a few options. Pinch (a "
        "concierge med spa) sends nurse injectors to your home. Glow Mobile "
        "Aesthetics and RiverNorth Med Spa also offer visits.")
out = extract_providers(resp, ["pinch", "bookpinch", "pinchmed"])
print("pinch_present:", out.pinch_present)
print("pinch_position:", out.pinch_position)
print("providers:", [(p.name, p.position) for p in out.providers])
assert out.pinch_present is True
assert any("pinch" in p.name.lower() for p in out.providers)
```

Run: `python scratch_extract.py`
Expected: `pinch_present: True`, Pinch in the providers list, plus the two competitors. Delete the file after it passes.

- [ ] **Step 4: Commit**

```bash
git add geo/parser.py
git commit -m "feat: emergent provider extraction (replaces per-competitor scoring)"
```

---

## Task 5: Orchestrator — city dimension, citations, emergent persistence

**Files:**
- Modify: `geo/orchestrator.py`

**Interfaces:**
- Consumes: `geo.config.load_cities/load_queries/load_brand/expand_cells/brand_domain_cited`, `geo.llms.generate`, `geo.parser.extract_with_retry`.
- Produces: populated SQLite at `data/results.sqlite` with the new schema below. CLI: `python -m geo.orchestrator [--runs N] [--models ...] [--dry-run]`.

> **Testing note:** The full run is live/expensive; verify with `--dry-run` (Step 6) and a tiny real slice (Step 7). The new schema is the reviewable deliverable.

- [ ] **Step 1: Replace `SCHEMA`** in `geo/orchestrator.py`

```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    model TEXT NOT NULL,
    city TEXT NOT NULL,
    query_id TEXT NOT NULL,
    segment TEXT NOT NULL,
    run_index INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    raw_response TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    response_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    UNIQUE(run_date, model, city, query_id, run_index)
);

CREATE TABLE IF NOT EXISTS extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id INTEGER NOT NULL,
    pinch_present INTEGER NOT NULL,
    pinch_position INTEGER,
    pinch_cited INTEGER NOT NULL,
    providers_json TEXT NOT NULL,
    evidence_quote TEXT,
    FOREIGN KEY(response_id) REFERENCES responses(id)
);
CREATE INDEX IF NOT EXISTS idx_extr_resp ON extractions(response_id);
CREATE INDEX IF NOT EXISTS idx_resp_cell ON responses(city, model, query_id);
"""
```

- [ ] **Step 2: Rewrite `run_battery`** to iterate cells and persist emergent data

```python
def run_battery(runs_per_cell: int = 3,
                models: list[ModelName] = None):
    init_db()
    cities = config.load_cities()
    queries = config.load_queries()
    brand = config.load_brand()
    cells = config.expand_cells(cities, queries)
    models = models or ALL_MODELS

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    con = sqlite3.connect(DB_PATH)

    n_total = len(cells) * len(models) * runs_per_cell
    n_done = n_skipped = 0
    started = time.time()

    for cell in cells:
        for model in models:
            for run_idx in range(1, runs_per_cell + 1):
                n_done += 1
                row = con.execute(
                    "SELECT id FROM responses WHERE run_date=? AND model=? "
                    "AND city=? AND query_id=? AND run_index=?",
                    (today, model, cell["city"], cell["query_id"], run_idx),
                ).fetchone()
                if row is not None:
                    n_skipped += 1
                    continue

                try:
                    resp = generate(model, cell["prompt"], max_tokens=2000)
                except Exception as e:
                    print(f" [{n_done}/{n_total}] {model}/{cell['city']}/"
                          f"{cell['query_id']}/r{run_idx} GENERATE FAILED: {e}")
                    continue

                cur = con.execute(
                    "INSERT INTO responses (run_date, model, city, query_id, "
                    "segment, run_index, prompt, raw_response, citations_json, "
                    "response_tokens, cost_usd) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (today, model, cell["city"], cell["query_id"],
                     cell["segment"], run_idx, cell["prompt"], resp.text,
                     json.dumps(resp.citations), resp.output_tokens,
                     resp.cost_usd),
                )
                response_id = cur.lastrowid
                con.commit()

                extraction = extract_with_retry(resp.text, brand["aliases"])
                if extraction is not None:
                    pinch_cited = config.brand_domain_cited(
                        brand["domain"], resp.citations)
                    con.execute(
                        "INSERT INTO extractions (response_id, pinch_present, "
                        "pinch_position, pinch_cited, providers_json, "
                        "evidence_quote) VALUES (?,?,?,?,?,?)",
                        (response_id, 1 if extraction.pinch_present else 0,
                         extraction.pinch_position, 1 if pinch_cited else 0,
                         json.dumps([{"name": p.name, "position": p.position}
                                     for p in extraction.providers]),
                         extraction.evidence_quote),
                    )
                    con.commit()

                elapsed = time.time() - started
                avg = elapsed / max(1, n_done - n_skipped)
                eta = avg * (n_total - n_done)
                print(f" [{n_done}/{n_total}] {model}/{cell['city']}/"
                      f"{cell['query_id']}/r{run_idx} done "
                      f"cost=${resp.cost_usd:.3f} eta={int(eta/60)}m")

    con.close()
    print(f"\n[done] {n_done} cells, {n_skipped} skipped, "
          f"elapsed {int((time.time()-started)/60)}m")
```

- [ ] **Step 3: Update imports** at the top of `geo/orchestrator.py`

```python
from . import config
from .llms import generate, ALL_MODELS, ModelName
from .parser import extract_with_retry
```

(Remove the old `from .parser import score_one_with_retry` import.)

- [ ] **Step 4: Rewrite the `__main__` block** (drop `--queries/--competitors`, keep `--runs/--models/--dry-run`)

```python
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Run the Pinch GEO battery.")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--models", nargs="+", default=None,
                    help="Subset of models. Default: all 4.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        cities = config.load_cities()
        queries = config.load_queries()
        models = args.models or ALL_MODELS
        n_cells = len(cities) * len(queries) * len(models) * args.runs
        print("DRY RUN")
        print(f" cities: {len(cities)}  queries: {len(queries)}")
        print(f" models: {len(models)}  runs/cell: {args.runs}")
        print(f" total generations: {n_cells}")
        print(f" est cost: LLM+search ${n_cells * 0.02:.2f}, "
              f"Firecrawl parse ${n_cells * 0.02:.2f}")
    else:
        run_battery(runs_per_cell=args.runs, models=args.models)
```

- [ ] **Step 5: If a stale `data/results.sqlite` exists with the old schema, reset it**

Run: `rm -f data/results.sqlite`
(The old DB has the Firecrawl-competitor schema; the new schema differs. A fresh file is correct for this new measurement.)

- [ ] **Step 6: Verify dry-run**

Run: `python -m geo.orchestrator --dry-run`
Expected: prints cities=5, queries=7, models=4, runs/cell=3, total generations=420.

- [ ] **Step 7: Real slice smoke test (small + cheap)**

Run: `python -m geo.orchestrator --runs 1 --models perplexity`
Expected: ~35 generations complete; then
Run: `sqlite3 data/results.sqlite "SELECT city, count(*) FROM responses GROUP BY city; SELECT count(*) FROM extractions; SELECT pinch_present, pinch_cited FROM extractions LIMIT 5;"`
Expected: 5 cities populated, extractions rows present, boolean columns 0/1. Re-running the same command should skip all (idempotent) — verify it prints `35 skipped`.

- [ ] **Step 8: Commit**

```bash
git add geo/orchestrator.py
git commit -m "feat: orchestrator with city dimension + emergent persistence"
```

---

## Task 6: Scoring — Presence Rate, leaderboard, citation rate

**Files:**
- Rewrite: `geo/score.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Produces:
  - `geo.score.presence_rates(db_path=DB_PATH) -> list[dict]` — one row per `(city, model)`: `{city, model, n, presence_rate, citation_rate}`.
  - `geo.score.competitor_leaderboard(db_path=DB_PATH) -> dict[str, list[dict]]` — per city, providers sorted by mention count: `{city: [{name, mentions, share_of_voice}, ...]}`.
  - `geo.score.export_dashboard_data(out_path="dashboard/data.json", db_path=DB_PATH) -> None`.

- [ ] **Step 1: Write the failing test** — `tests/test_scoring.py`

```python
import json
import sqlite3
from pathlib import Path

from geo import score


def _seed(db: Path):
    con = sqlite3.connect(db)
    con.executescript("""
      CREATE TABLE responses (id INTEGER PRIMARY KEY, run_date TEXT,
        model TEXT, city TEXT, query_id TEXT, segment TEXT, run_index INTEGER,
        prompt TEXT, raw_response TEXT, citations_json TEXT,
        response_tokens INTEGER, cost_usd REAL);
      CREATE TABLE extractions (id INTEGER PRIMARY KEY, response_id INTEGER,
        pinch_present INTEGER, pinch_position INTEGER, pinch_cited INTEGER,
        providers_json TEXT, evidence_quote TEXT);
    """)
    # Chicago/perplexity: 2 responses, Pinch present in 1, cited in 1.
    con.execute("INSERT INTO responses (id, city, model, citations_json) "
                "VALUES (1,'Chicago','perplexity','[]')")
    con.execute("INSERT INTO responses (id, city, model, citations_json) "
                "VALUES (2,'Chicago','perplexity','[]')")
    con.execute("INSERT INTO extractions (response_id, pinch_present, "
                "pinch_position, pinch_cited, providers_json, evidence_quote) "
                "VALUES (1,1,1,1,'[{\"name\":\"Pinch\",\"position\":1},"
                "{\"name\":\"Glow MedSpa\",\"position\":2}]','q')")
    con.execute("INSERT INTO extractions (response_id, pinch_present, "
                "pinch_position, pinch_cited, providers_json, evidence_quote) "
                "VALUES (2,0,NULL,0,'[{\"name\":\"Glow MedSpa\","
                "\"position\":1}]','')")
    con.commit(); con.close()


def test_presence_and_citation_rate(tmp_path):
    db = tmp_path / "t.sqlite"; _seed(db)
    rows = score.presence_rates(db_path=db)
    row = next(r for r in rows if r["city"] == "Chicago"
               and r["model"] == "perplexity")
    assert row["n"] == 2
    assert row["presence_rate"] == 0.5
    assert row["citation_rate"] == 0.5


def test_competitor_leaderboard_share_of_voice(tmp_path):
    db = tmp_path / "t.sqlite"; _seed(db)
    board = score.competitor_leaderboard(db_path=db)["Chicago"]
    glow = next(p for p in board if p["name"] == "Glow MedSpa")
    assert glow["mentions"] == 2          # named in both responses
    # 3 total mentions (Pinch 1 + Glow 2) -> Glow share = 2/3
    assert round(glow["share_of_voice"], 2) == 0.67


def test_export_writes_json(tmp_path):
    db = tmp_path / "t.sqlite"; _seed(db)
    out = tmp_path / "data.json"
    score.export_dashboard_data(out_path=str(out), db_path=db)
    payload = json.loads(out.read_text())
    assert "presence" in payload and "leaderboard" in payload
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/test_scoring.py -v`
Expected: FAIL — functions not defined / signature mismatch.

- [ ] **Step 3: Rewrite `geo/score.py`**

```python
"""Aggregate emergent extractions into Presence Rate + competitor leaderboard."""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

DB_PATH = Path("data/results.sqlite")


def _connect(db_path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def presence_rates(db_path=DB_PATH) -> list[dict]:
    """Presence Rate + citation rate per (city, model)."""
    con = _connect(db_path)
    rows = con.execute("""
        SELECT r.city AS city, r.model AS model,
               COUNT(*) AS n,
               AVG(e.pinch_present) AS presence_rate,
               AVG(e.pinch_cited) AS citation_rate
        FROM extractions e JOIN responses r ON r.id = e.response_id
        GROUP BY r.city, r.model
    """).fetchall()
    con.close()
    return [{"city": r["city"], "model": r["model"], "n": r["n"],
             "presence_rate": round(r["presence_rate"] or 0.0, 4),
             "citation_rate": round(r["citation_rate"] or 0.0, 4)}
            for r in rows]


def competitor_leaderboard(db_path=DB_PATH) -> dict[str, list[dict]]:
    """Per city: every provider named, ranked by mention count, with SoV."""
    con = _connect(db_path)
    rows = con.execute("""
        SELECT r.city AS city, e.providers_json AS providers
        FROM extractions e JOIN responses r ON r.id = e.response_id
    """).fetchall()
    con.close()

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        for p in json.loads(row["providers"]):
            counts[row["city"]][p["name"].strip()] += 1

    board: dict[str, list[dict]] = {}
    for city, provs in counts.items():
        total = sum(provs.values()) or 1
        board[city] = sorted(
            [{"name": n, "mentions": c,
              "share_of_voice": round(c / total, 4)}
             for n, c in provs.items()],
            key=lambda d: -d["mentions"])
    return board


def export_dashboard_data(out_path: str = "dashboard/data.json",
                          db_path=DB_PATH) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brand": "Pinch",
        "presence": presence_rates(db_path),
        "leaderboard": competitor_leaderboard(db_path),
    }
    Path(out_path).parent.mkdir(exist_ok=True)
    Path(out_path).write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_path}: {len(payload['presence'])} (city,model) cells")


if __name__ == "__main__":
    export_dashboard_data()
```

- [ ] **Step 4: Run test, verify it passes**

Run: `pytest tests/test_scoring.py -v`
Expected: 3 passed.

- [ ] **Step 5: Export from the real slice DB**

Run: `python -m geo.score`
Expected: writes `dashboard/data.json` with `presence` rows for the Chicago/Phoenix/… × perplexity cells from Task 5's slice.

- [ ] **Step 6: Commit**

```bash
git add geo/score.py tests/test_scoring.py
git commit -m "feat: Presence Rate scoring + emergent competitor leaderboard"
```

---

## Task 7: Dashboard — city×engine presence heatmap + leaderboard

**Files:**
- Rework: `dashboard/index.html`, `dashboard/dashboard.js`

**Interfaces:**
- Consumes: `dashboard/data.json` shape from Task 6 (`presence: [{city, model, n, presence_rate, citation_rate}]`, `leaderboard: {city: [{name, mentions, share_of_voice}]}`).

> **Testing note:** Visual verification (Step 4). No unit test — this is presentation.

- [ ] **Step 1: Rewrite `dashboard/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pinch — GEO Visibility Snapshot</title>
  <style>
    body { font: 15px/1.5 -apple-system, system-ui, sans-serif; margin: 2rem;
           color: #1a1a1a; max-width: 1000px; }
    h1 { margin-bottom: .25rem; }
    .sub { color: #666; margin-top: 0; }
    table { border-collapse: collapse; margin: 1rem 0 2rem; }
    th, td { padding: .5rem .75rem; text-align: center; border: 1px solid #eee; }
    th { background: #fafafa; }
    .heat { color: #fff; font-weight: 600; }
    h2 { margin-top: 2rem; }
    .board { display: flex; flex-wrap: wrap; gap: 1.5rem; }
    .city-card { border: 1px solid #eee; border-radius: 8px; padding: 1rem;
                 min-width: 240px; }
    .city-card h3 { margin: 0 0 .5rem; }
    .bar { background: #f0f0f0; border-radius: 4px; height: 18px;
           position: relative; margin: 3px 0; }
    .bar > span { position: absolute; left: 6px; font-size: 12px;
                  line-height: 18px; }
    .bar > i { display: block; height: 100%; border-radius: 4px;
               background: #c4410c; opacity: .25; }
    .pinch > i { opacity: 1; }
  </style>
</head>
<body>
  <h1>Pinch — GEO Visibility Snapshot</h1>
  <p class="sub" id="subtitle"></p>

  <h2>Presence Rate — how often an AI names Pinch</h2>
  <p class="sub">% of answers naming Pinch, by city and engine. Higher = more
     visible. Citation rate (bookpinch.com cited as a source) shown in
     parentheses.</p>
  <div id="heatmap"></div>

  <h2>Who the AI recommends instead (emergent competitors)</h2>
  <p class="sub">Every provider the engines named, by city. Pinch highlighted.</p>
  <div class="board" id="leaderboard"></div>

  <script src="dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 2: Rewrite `dashboard/dashboard.js`**

```javascript
function heatColor(rate) {
  // 0 -> light grey, 1 -> Pinch orange
  const r = Math.round(0xf0 + (0xc4 - 0xf0) * rate);
  const g = Math.round(0xf0 + (0x41 - 0xf0) * rate);
  const b = Math.round(0xf0 + (0x0c - 0xf0) * rate);
  return `rgb(${r},${g},${b})`;
}

async function main() {
  const data = await fetch('data.json').then(r => r.json());
  document.getElementById('subtitle').textContent =
    `Brand: ${data.brand} · generated ${new Date(data.generated_at)
      .toLocaleString()}`;

  const cities = [...new Set(data.presence.map(p => p.city))];
  const models = [...new Set(data.presence.map(p => p.model))];
  const lookup = {};
  data.presence.forEach(p => { lookup[`${p.city}|${p.model}`] = p; });

  // ---- Heatmap table ----
  let html = '<table><thead><tr><th>City \\ Engine</th>' +
    models.map(m => `<th>${m}</th>`).join('') + '</tr></thead><tbody>';
  for (const city of cities) {
    html += `<tr><th>${city}</th>`;
    for (const m of models) {
      const cell = lookup[`${city}|${m}`];
      if (!cell) { html += '<td>—</td>'; continue; }
      const pr = (cell.presence_rate * 100).toFixed(0);
      const cr = (cell.citation_rate * 100).toFixed(0);
      html += `<td class="heat" style="background:${heatColor(
        cell.presence_rate)}">${pr}% <small>(${cr}%)</small></td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  document.getElementById('heatmap').innerHTML = html;

  // ---- Competitor leaderboard ----
  const board = document.getElementById('leaderboard');
  for (const city of Object.keys(data.leaderboard)) {
    const card = document.createElement('div');
    card.className = 'city-card';
    const top = data.leaderboard[city].slice(0, 8);
    const max = Math.max(...top.map(p => p.mentions), 1);
    card.innerHTML = `<h3>${city}</h3>` + top.map(p => {
      const isPinch = /pinch/i.test(p.name);
      const w = (p.mentions / max * 100).toFixed(0);
      return `<div class="bar ${isPinch ? 'pinch' : ''}">
        <i style="width:${w}%"></i>
        <span>${p.name} · ${p.mentions}</span></div>`;
    }).join('');
    board.appendChild(card);
  }
}

main();
```

- [ ] **Step 3: Note** — the old dashboard loaded Chart.js and referenced Firecrawl-specific DOM ids (`firecrawl-score`, `rankingChart`). This rewrite drops Chart.js entirely (heatmap + bars are pure HTML/CSS), so no external script tag is needed. Confirm `index.html` has no leftover `<script src="...chart...">` tags.

- [ ] **Step 4: Visual verification**

Run: `cd dashboard && python -m http.server 8000`
Open `http://localhost:8000`. Expected: a city×engine grid with orange-shaded Presence cells (from the perplexity slice; other engines show "—" until a full run), and per-city competitor bars with Pinch highlighted. Ctrl-C to stop.

- [ ] **Step 5: Commit**

```bash
git add dashboard/index.html dashboard/dashboard.js
git commit -m "feat: presence heatmap + emergent competitor dashboard"
```

---

## Task 8: Docs — README + methodology, and the full run

**Files:**
- Modify: `README.md`
- Modify/Note: `docs/scoring-methodology.pdf` (regenerated via `scripts/generate_docs.py` if that script is retargeted; otherwise update README only and note the PDF is stale).

- [ ] **Step 1: Rewrite `README.md`** top-to-bottom to describe the Pinch measurement

```markdown
# Pinch GEO Visibility Snapshot

Measures how often AI engines name **Pinch** (at-home med spa, bookpinch.com)
when consumers ask local aesthetics questions — across cities and engines.

## Methodology

**Cities.** Chicago (anchor) + Phoenix, Denver, Seattle, Washington DC.
Editable in `cities.json` — adding a market is one line.

**Queries.** ~7 city-templated consumer prompts across intents (discovery,
category intent, service-specific, occasion, brand-aware) in `queries.json`.
Each runs 3× per engine.

**Engines.** Claude, GPT, Gemini, Perplexity — **all web-grounded** (live
search), because the models have no training-data knowledge of a small local
brand. Ungrounded results would be hallucinated.

**Emergent competitors.** Instead of a fixed competitor list, the Firecrawl
`/parse` judge extracts *every provider each answer names*. Competitors emerge
per city — which is what makes the method reusable for new expansion cities.

**Headline metric — Presence Rate.** The fraction of answers that name Pinch,
per city and engine. Objective, per-answer yes/no. Diagnostics: Pinch's rank
when present, share-of-voice vs emergent competitors, and citation rate
(is bookpinch.com cited as a source).

## Known limitation

API-grounded answers approximate, but do not perfectly equal, what a person
sees in the consumer ChatGPT / Perplexity / Gemini apps. Standard, defensible
way to measure GEO at scale — but an approximation.

## Reproducing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC/OPENAI/GEMINI/PERPLEXITY/FIRECRAWL keys
python -m geo.orchestrator --dry-run     # check the plan (420 generations)
python -m geo.orchestrator               # full run
python -m geo.score                      # export dashboard/data.json
cd dashboard && python -m http.server 8000
```
```

- [ ] **Step 2: Create `.env.example`**

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
PERPLEXITY_API_KEY=
FIRECRAWL_API_KEY=
```

- [ ] **Step 3: Commit docs**

```bash
git add README.md .env.example
git commit -m "docs: rewrite README for Pinch GEO measurement"
```

- [ ] **Step 4: Full run (cost checkpoint — confirm with user first)**

Before running, re-confirm cost with the user (≈420 grounded generations + ≈420 Firecrawl parses). Then:

Run: `python -m geo.orchestrator` (expect ~60–90 min; watch the ETA line)
Then: `python -m geo.score`
Then reload the dashboard. Expected: all four engine columns populated across all five cities.

- [ ] **Step 5: Spot-check the parser (reuse the audit habit)**

Run: `sqlite3 data/results.sqlite "SELECT r.city, r.model, e.pinch_present, e.evidence_quote FROM extractions e JOIN responses r ON r.id=e.response_id WHERE e.pinch_present=1 LIMIT 15;"`
Read 10–15 evidence quotes against expectation; if the judge is over/under-calling Pinch presence, tighten the `extract_providers` prompt and re-run `--models <one>` for a spot fix.

- [ ] **Step 6: Final commit (committed data snapshot for the static dashboard)**

```bash
git add dashboard/data.json
git commit -m "data: Pinch GEO snapshot results"
```

---

## Self-Review Notes (author)

- **Spec coverage:** web grounding → Task 3; city dimension → Tasks 1 & 5; emergent competitors → Tasks 4 & 6; Presence Rate headline → Task 6; heatmap + leaderboard dashboard → Task 7; repeatable-by-config (`cities.json`) → Task 1; citation rate → Tasks 2/5/6; limitation documented → Task 8. All spec sections mapped.
- **Type consistency:** `Response.citations: list[str]` (Task 3) consumed as `resp.citations` (Task 5). `ProviderExtraction.{providers,pinch_present,pinch_position,evidence_quote}` (Task 4) consumed in Task 5's INSERT. `presence_rates`/`competitor_leaderboard`/`export_dashboard_data` signatures (Task 6) match `dashboard.js` payload keys `presence`/`leaderboard` and row fields (Task 7).
- **Deliberately unused:** old `CompetitorScore`/`score_one` in `parser.py` left in place (harmless, referenced by legacy `test_parser.py`); not wired into the new pipeline.
```
