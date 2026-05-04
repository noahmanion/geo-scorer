"""
run the full battery, persist results, support resume-from-failure.
"""
from __future__ import annotations
import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime, timezone

from .llms import generate, ALL_MODELS, ModelName
from .parser import score_one_with_retry

DB_PATH = Path("data/results.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    model TEXT NOT NULL,
    query_id TEXT NOT NULL,
    segment TEXT NOT NULL,
    run_index INTEGER NOT NULL,
    raw_response TEXT NOT NULL,
    response_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    UNIQUE(run_date, model, query_id, run_index)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id INTEGER NOT NULL,
    competitor TEXT NOT NULL,
    mentioned INTEGER NOT NULL,
    position INTEGER,
    strength INTEGER NOT NULL,
    context_quality INTEGER NOT NULL,
    confidence REAL,
    evidence_quote TEXT,
    FOREIGN KEY(response_id) REFERENCES responses(id)
);
CREATE INDEX IF NOT EXISTS idx_scores_recap ON scores(response_id);
CREATE INDEX IF NOT EXISTS idx_resp_query ON responses(query_id, model);

"""

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.commit()
    con.close()


def run_battery(
        queries_path: str = "queries.json",
        competitors_path: str = "competitors.json",
        # reducing this reduces cost, but you lose some statistical power 
        runs_per_cell: int = 2, 
        models: list[ModelName] = None,
):
    init_db()

    queries = json.loads(Path(queries_path).read_text())
    competitors = [c["name"] for c in
                   json.loads(Path(competitors_path).read_text())]
    models = models or ALL_MODELS

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    total_cost = 0.0

    con = sqlite3.connect(DB_PATH)

    n_total = len(queries) * len(models) * runs_per_cell
    n_done = 0
    n_skipped = 0
    started = time.time()

    for query in queries:
        for model in models:
            for run_idx in range(1 , runs_per_cell + 1):
                n_done += 1

                # in the db? skip it.
                row = con.execute(
                        "Select id from responses where run_date=? " \
                        "and model=? and query_id=? and run_index=? ",
                        (today, model, query["id"], run_idx)
                ).fetchone()
                if row is not None:
                    n_skipped += 1
                    continue

                # generate the LLM response
                try:
                    resp = generate(model, query["query"], max_tokens=400)
                except Exception as e:
                    print(f" [{n_done}/{n_total}] {model}/{query['id']}/r{run_idx}" f" GENERATE FAILED: {e}")
                    continue

                # 2: persist the response
                cur = con.execute(
                    "INSERT INTO responses (run_date, model, query_id, " \
                    "segment, run_index, raw_response, response_tokens, cost_usd) " \
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (today, model, query["id"], query["segment"], run_idx,
                     resp.text, resp.output_tokens, resp.cost_usd)
                )
                response_id = cur.lastrowid
                con.commit()

                # 3: score the response
                for competitor in competitors:
                    score = score_one_with_retry(resp.text, competitor)
                    if score is None:
                        continue
                    con.execute(
                        "INSERT INTO scores (response_id, competitor, " \
                        "mentioned, position, strength, context_quality, " \
                        "confidence, evidence_quote) " \
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (response_id, competitor, 1 if score.mentioned else 0,
                         score.position, score.strength, score.context_quality,
                         score.confidence, score.evidence_quote)
                    )

                con.commit()

                elapsed = time.time() - started
                avg = elapsed / max(1, n_done - n_skipped)
                eta = avg * (n_total - n_done)
                print(f" [{n_done}/{n_total}] {model}/{query['id']}/r{run_idx} "
                      f"done. cost=${resp.cost_usd:.3f} "
                      f"eta={int(eta/60)}m")

    con.close()
    print(f"\n[done] {n_done} cells, {n_skipped} skipped, "
          f"total cost=${total_cost:.3f} "
          f"elapsed {int((time.time()-started)/60)}m")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Run the GEO measurement battery."
    )
    parser.add_argument("--queries", default="queries.json")
    parser.add_argument("--competitors", default="competitors.json")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--models", nargs="+",
                        default=None,
                        help= "Subset of models. Default: All 4.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without making API calls.")
    args = parser.parse_args()

    if args.dry_run:
        queries = json.loads(Path(args.queries).read_text())
        competitors = json.loads(Path(args.competitors).read_text())
        models = args.models or ALL_MODELS
        n_cells = len(queries) * len(models) * args.runs
        n_scores = n_cells * len(competitors)
        print(f"DRY RUN")
        print(f" queries: {len(queries)}")
        print(f" models: {len(models)}")
        print(f" runs/cell: {args.runs}")
        print(f" competitors: {len(competitors)}")
        print(f" total cells: {n_cells}")
        print(f" total scores: {n_scores}")
        print(f" est cost: LLM ${n_cells * 0.005:.2f}, "
              f"FC ${n_scores * 0.02:.2f}")
    else:
        run_battery(
            queries_path=args.queries,
            competitors_path=args.competitors,
            runs_per_cell=args.runs,
            models=args.models,
        )
