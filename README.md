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

- Citation rate is a diagnostic, not the headline. Gemini's grounding exposes
  each source as an opaque `vertexaisearch.cloud.google.com` redirect URL, but
  its `web.title` field carries the real publisher domain — so we capture the
  domain from the title (e.g. `bookpinch.com`) instead of the redirect. For
  Gemini we therefore record source *domains*, not full URLs; other engines
  record full URLs. Presence Rate (the headline) is read from the answer text,
  not citations, so it is unaffected either way.

## Reproducing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC/OPENAI/GEMINI/PERPLEXITY/FIRECRAWL keys
python -m geo.orchestrator --dry-run     # check the plan (counts depend on cities.json x queries.json x --runs)
python -m geo.orchestrator               # full run
python -m geo.score                      # export dashboard/data.json
cd dashboard && python -m http.server 8000
```
