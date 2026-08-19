# GEO Rank Tracker

Measures how a product is recommended across major LLMs vs competitors. The example data is for Firecrawl.

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
