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

- Citation rate is a diagnostic, not the headline. Gemini's grounding returns
  opaque `vertexaisearch.cloud.google.com` redirect URLs rather than publisher
  domains, so bookpinch.com is never matched as a Gemini citation — Gemini's
  citation rate reads near-zero regardless of actual sourcing. Presence Rate
  (the headline) is unaffected because it is read from the answer text, not
  citations.

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
