# Requirements: Firecrawl GEO Intelligence PoC

**Defined:** 2026-05-06
**Core Value:** Know where Firecrawl stands in LLM recommendations across query segments

## v1 Requirements

### Data Collection

- [ ] **COLL-01**: System can run a battery of queries against Claude, GPT, Gemini, and Perplexity
- [ ] **COLL-02**: LLM responses are persisted to SQLite with deduplication (resume-from-failure)
- [ ] **COLL-03**: Dry-run mode prints plan without making API calls
- [ ] **COLL-04**: CLI supports filtering to a subset of models and queries

### Scoring

- [ ] **SCOR-01**: Each response is scored against each competitor via Firecrawl structured extraction
- [ ] **SCOR-02**: Scorer captures: mentioned (bool), position (int), strength (0–3), context_quality (0–3), confidence (float), evidence_quote (str)
- [ ] **SCOR-03**: One parser call per (response, competitor) to avoid position bias
- [ ] **SCOR-04**: Parser retries on transient failures (up to 3 attempts with backoff)

### Analysis

- [ ] **ANLY-01**: GEO score computed per (model, segment, competitor) cell using weighted formula
- [ ] **ANLY-02**: Scores normalized 0–10 across the full matrix
- [ ] **ANLY-03**: Standard deviation computed per cell for error bars
- [ ] **ANLY-04**: Headline score aggregated per competitor across all cells (weighted by n_obs)

### Dashboard

- [ ] **DASH-01**: Static dashboard shows Firecrawl's headline GEO score and rank
- [ ] **DASH-02**: Horizontal bar chart shows all competitors ranked by GEO score
- [ ] **DASH-03**: Grouped bar chart shows performance by query segment
- [ ] **DASH-04**: Dashboard deployed on Vercel, served from committed data.json

### Audit

- [ ] **AUDT-01**: Spot-check tool samples 30 random (response, score) pairs for manual review
- [ ] **AUDT-02**: Spot-check results saved to data/spot_check.json with agreement rate

## v2 Requirements

### Automation

- **AUTO-01**: Scheduled runs (daily/weekly) without manual CLI invocation
- **AUTO-02**: Automatic dashboard data refresh after each run
- **AUTO-03**: Alerts when Firecrawl rank drops below threshold

### Expanded Coverage

- **EXPD-01**: Agent-loop coverage (Cursor / Claude Code recommendations)
- **EXPD-02**: Additional query segments (e.g. enterprise, security)
- **EXPD-03**: Cross-model judge comparison (reduce self-enhancement bias)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-brand / self-serve product | Internal use only for now |
| Real-time scoring | Batch pipeline sufficient for intelligence cadence |
| Attribution / conversion tracking | GEO score ≠ signup signal; different instrumentation needed |
| Mobile app | Static web dashboard sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COLL-01 | Phase 1 | Complete |
| COLL-02 | Phase 1 | Complete |
| COLL-03 | Phase 1 | Complete |
| COLL-04 | Phase 1 | Complete |
| SCOR-01 | Phase 1 | Complete |
| SCOR-02 | Phase 1 | Complete |
| SCOR-03 | Phase 1 | Complete |
| SCOR-04 | Phase 1 | Complete |
| ANLY-01 | Phase 2 | Complete |
| ANLY-02 | Phase 2 | Complete |
| ANLY-03 | Phase 2 | Complete |
| ANLY-04 | Phase 2 | Complete |
| DASH-01 | Phase 2 | Complete |
| DASH-02 | Phase 2 | Complete |
| DASH-03 | Phase 2 | Complete |
| DASH-04 | Phase 2 | Complete |
| AUDT-01 | Phase 2 | Complete |
| AUDT-02 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after initial definition*
