"""
interactive parser audit.
pulls 30 random (response, score) pairs and asks you to grade each
"""
import sqlite3
import random
import json
from pathlib import Path

DB = Path("data/results.sqlite")
SAMPLE_N = 30


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    
    rows = con.execute("""
        SELECT
            s.id AS sid, s.competitor, s.mentioned, s.position,
            s.strength, s.context_quality, s.confidence,
            s.evidence_quote,
            r.model, r.segment, r.query_id, r.raw_response
        FROM scores s
        JOIN responses r ON r.id = s.response_id
        ORDER BY RANDOM()
        LIMIT ?
        """, (SAMPLE_N,)).fetchall()
    
    results = []
    for i, row in enumerate(rows, 1):
        print(f"\n{'='*70}")
        print(f"[{i}/{SAMPLE_N}] model={row['model']} "
        f"segment={row['segment']} query={row['query_id']}")
        print(f"competitor: {row['competitor']}")
        print(f"\n--- LLM RESPONSE ---")
        print(row["raw_response"][:800])
        if len(row["raw_response"]) > 800:
            print(f"... [{len(row['raw_response'])-800} chars more]")
        print(f"\n--- PARSER OUTPUT ---")
        print(f" mentioned: {bool(row['mentioned'])}")
        print(f" position: {row['position']}")
        print(f" strength: {row['strength']}")
        print(f" context_quality: {row['context_quality']}")
        print(f" evidence_quote: {row['evidence_quote']!r}")

        verdict = input("\nAgree? [y/n/s=skip]: ").strip().lower()
        if verdict == "s":
            continue
        notes = ""
        if verdict == "n":
            notes = input("What's wrong? ").strip()

        results.append({
            "score_id": row["sid"],
            "competitor": row["competitor"],
            "model": row["model"],
            "agree": verdict == "y",
            "notes": notes,
        })

    Path("data/spot_check.json").write_text(json.dumps(results, indent=2))

    n = len(results)
    n_agree = sum(1 for r in results if r["agree"])
    print(f"\n{'='*70}")
    print(f"Results: {n_agree}/{n} agreed ({100*n_agree/n:.1f}%)")
    print(f"Saved to data/spot_check.json")


if __name__ == "__main__":
    main()