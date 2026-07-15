"""Aggregate emergent extractions into Presence Rate + competitor leaderboard."""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

from geo.config import load_brand

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


def _make_canonicalizer(brand: dict):
    """Build a function that folds provider-name spelling variants together.

    Any name containing a brand alias (casefolded substring match) collapses
    to the exact brand name. Everything else collapses on case/whitespace
    only, keeping the first-seen spelling for display. This intentionally
    does NOT attempt fuzzy/semantic matching between distinct competitors.
    """
    brand_name = brand["name"]
    aliases = [a.casefold() for a in brand.get("aliases", [])]
    display_names: dict[str, str] = {}

    def canonicalize(raw_name: str) -> str:
        folded = raw_name.casefold()
        if any(alias in folded for alias in aliases):
            return brand_name
        key = " ".join(folded.split())
        if key not in display_names:
            display_names[key] = raw_name.strip()
        return display_names[key]

    return canonicalize


def competitor_leaderboard(db_path=DB_PATH) -> dict[str, list[dict]]:
    """Per city: every provider named, ranked by mention count, with SoV."""
    canonicalize = _make_canonicalizer(load_brand())

    con = _connect(db_path)
    rows = con.execute("""
        SELECT r.city AS city, e.providers_json AS providers
        FROM extractions e JOIN responses r ON r.id = e.response_id
    """).fetchall()
    con.close()

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        try:
            providers = json.loads(row["providers"])
        except (json.JSONDecodeError, TypeError):
            continue
        for p in providers:
            counts[row["city"]][canonicalize(p["name"])] += 1

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