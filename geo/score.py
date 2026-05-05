"""
aggregate raw scores into GEO per cell.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
import math
from dataclasses import dataclass
import json
from datetime import datetime, timezone


DB_PATH = Path("data/results.sqlite")

## Weights from 0.2. Configureable for sensitivity analysis.
W_MENTION = 3.0
W_STRENGTH = 2.0
W_CONTEXT = 1.5
W_POSITION = 0.3

AGGREGATE_SQL = """
SELECT
    r.model as model,
    r.segment as segment,
    s.competitor as competitor,
    count(*) as n_obs,
    avg(s.mentioned) as mentioned_rate,
    -- conditional averages: only count rows when mentioned
    AVG(CASE WHEN s.mentioned=1 THEN s.strength END)
        AS avg_strength,
    AVG(CASE WHEN s.mentioned=1 THEN s.context_quality END)
        AS avg_context,
    AVG(CASE WHEN s.mentioned=1 THEN s.position END)
        AS avg_position
FROM scores s
JOIN responses r ON r.id = s.response_id
GROUP BY r.model, r.segment, s.competitor
"""

@dataclass
class CellScore:
    model: str
    segment: str
    competitor: str
    n_obs: int
    mentioned_rate: float
    avg_strength: float | None
    avg_context: float | None
    avg_position: float | None
    geo_score: float

def _compute_geo_(row: sqlite3.Row) -> float:
    ## Apply the weighted formula to one row. Handles NULL values.
    mention = row["mentioned_rate"] or 0.0
    strength = row["avg_strength"] or 0.0
    context = row["avg_context"] or 0.0
    position = row["avg_position"] if row["avg_position"] else 5.0

    return(
        W_MENTION * mention +
        W_STRENGTH * strength +
        W_CONTEXT * context -
        W_POSITION * position
    )

def aggregate() -> list[CellScore]:
    ## Compute GEO scores for every (model, segment, competitor) cell.
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = con.execute(AGGREGATE_SQL).fetchall()
    cells = []
    for r in rows:
        cells.append(CellScore(
            model=r["model"],
            segment=r["segment"],
            competitor=r["competitor"],
            n_obs=r["n_obs"],
            mentioned_rate=r["mentioned_rate"],
            avg_strength=r["avg_strength"],
            avg_context=r["avg_context"],
            avg_position=r["avg_position"],
            geo_score=_compute_geo_(r),
        ))

    con.close()
    return cells

def normalize(cells: list[CellScore]) -> list[CellScore]:
    """
    Linear scale GEO scores to 0-10 across the entire matrix.
    Anchor: max observed score -> 10. Min observed -> 0
    """
    scores = [c.geo_score for c in cells]
    lo, hi = min(scores), max(scores)
    rng = hi - lo if hi != lo else 1.0

    out = []
    for c in cells:
        normalized = 10.0 * (c.geo_score - lo) / rng
        out.append(CellScore(
            model=c.model,
            segment=c.segment,
            competitor=c.competitor,
            n_obs=c.n_obs,
            mentioned_rate=c.mentioned_rate,
            avg_strength=c.avg_strength,
            avg_context=c.avg_context,
            avg_position=c.avg_position,
            geo_score=normalized,
        ))
    return out
STDDEV_SQL = """
    WITH per_run AS (
        SELECT
            r.model,
            r.segment,
            s.competitor,
            r.run_index,
            AVG(s.strength) AS run_strength,
            AVG(s.mentioned) AS run_mention
        FROM scores s
        JOIN responses r ON r.id = s.response_id
        GROUP BY r.model, r.segment, s.competitor, r.run_index
        )

    SELECT
        model,
        segment,
        competitor,
        -- SQLite has no STDDEV, compute via avg-of-squares trick
        AVG(run_strength) AS mean_strength,
        AVG(run_mention) AS mean_mention,
        AVG(run_strength * run_strength) - AVG(run_strength) * AVG(run_strength)
        AS var_strength,
        AVG(run_mention * run_mention) - AVG(run_mention) * AVG(run_mention)
        AS var_mention
    FROM per_run
    GROUP BY model, segment, competitor
"""

def stddevs() -> dict[tuple[str, str, str], dict]:
    ## Returns dict keyed by (model, segment, competitor) with stddev fields,
    ## user to attach error bars to the cells in the dashboard.
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(STDDEV_SQL).fetchall()
    out = {}
    for r in rows:
        out[(r["model"], r["segment"], r["competitor"])] = {
            "stddev_strength": math.sqrt(max(0.0, r["var_strength"] or 0)),
            "stddev_mention": math.sqrt(max(0.0, r["var_mention"] or 0)),
        }
    con.close()
    return out

def headline_score(competitor: str = "Firecrawl",
                   cells: list[CellScore] = None) -> dict:
    ## Computer the overall GEO score for one competitor across the matric.
    ## Plus n_obs and the segment ranking among all competitors.
    if cells is None:
        cells = normalize(aggregate())

    ## filter to this competitor
    relevant = [c for c in cells if c.competitor == competitor]
    if not relevant:
        return {"competitor": competitor, "geo_score": 0.0, "n_obs": 0}
    
    total_obs = sum(c.n_obs for c in relevant)
    weighted_score = sum(c.geo_score * c.n_obs for c in relevant) / total_obs

    return {
        "competitor": competitor,
        "geo_score": weighted_score,
        "n_obs": total_obs,
        "n_cells": len(relevant),
    }

def all_competitors_ranked() -> list[dict]:
    # headline scores for every competiutor sorted high to low.
    cells = normalize(aggregate())
    competitors = sorted(set(c.competitor for c in cells))
    headlines = [headline_score(c, cells) for c in competitors]
    return sorted(headlines, key=lambda h: -h["geo_score"])

def export_dashboard_data(out_path: str = "dashboard/data.json"):
    ## Dump everthing the dshboard needs into one json file
    cells = normalize(aggregate())
    sd = stddevs()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "headline": all_competitors_ranked(),
        "cells": [
            {
                "model": c.model,
                "segment": c.segment,
                "competitor": c.competitor,
                "n_obs": c.n_obs,
                "mentioned_rate": round(c.mentioned_rate, 3),
                "avg_strength": round(c.avg_strength or 0.0, 2),
                "avg_context": round(c.avg_context or 0.0, 2),
                "geo_score": round(c.geo_score, 2),
                "stddev_strength": round(
                    sd.get((c.model, c.segment, c.competitor),
                    {}).get("stddev_strength", 0.0), 3
                ),
            }
            for c in cells
        ],
    }
    Path(out_path).parent.mkdir(exist_ok=True)
    Path(out_path).write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_path}: {len(payload['cells'])} cells")

if __name__ == "__main__":
    export_dashboard_data()