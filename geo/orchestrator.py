"""
run the full battery, persist results, support resume-from-failure.
"""
from __future__ import annotations
import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime, timezone

from . import config
from .llms import generate, ALL_MODELS, ModelName
from .parser import extract_with_retry

DB_PATH = Path("data/results.sqlite")

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

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.commit()
    con.close()


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
