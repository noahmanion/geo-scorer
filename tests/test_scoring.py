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


def test_competitor_leaderboard_canonicalizes_pinch_spellings(tmp_path):
    db = tmp_path / "t.sqlite"
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
    con.execute("INSERT INTO responses (id, city, model, citations_json) "
                "VALUES (1,'Austin','perplexity','[]')")
    con.execute("INSERT INTO responses (id, city, model, citations_json) "
                "VALUES (2,'Austin','perplexity','[]')")
    con.execute("INSERT INTO extractions (response_id, pinch_present, "
                "pinch_position, pinch_cited, providers_json, evidence_quote) "
                "VALUES (1,1,1,1,'[{\"name\":\"Pinch\",\"position\":1},"
                "{\"name\":\"Glow MedSpa\",\"position\":2}]','q')")
    con.execute("INSERT INTO extractions (response_id, pinch_present, "
                "pinch_position, pinch_cited, providers_json, evidence_quote) "
                "VALUES (2,1,1,1,'[{\"name\":\"Pinch Med Spa\",\"position\":1},"
                "{\"name\":\"Glow MedSpa\",\"position\":2}]','q')")
    con.commit(); con.close()

    board = score.competitor_leaderboard(db_path=db)["Austin"]
    pinch_rows = [p for p in board if p["name"] == "Pinch"]
    assert len(pinch_rows) == 1
    assert pinch_rows[0]["mentions"] == 2


def test_presence_by_engine_aggregates_across_cities(tmp_path):
    db = tmp_path / "t.sqlite"; _seed(db)
    rows = score.presence_by_engine(db_path=db)
    ppl = next(r for r in rows if r["model"] == "perplexity")
    assert ppl["n"] == 2
    assert ppl["presence_rate"] == 0.5


def test_response_details_shape_and_canonicalization(tmp_path):
    db = tmp_path / "t.sqlite"; _seed(db)
    details = score.response_details(db_path=db)
    assert len(details) == 2
    d = details[0]
    # every drill-down field is present
    for key in ("city", "model", "query_id", "segment", "query", "answer",
                "pinch_present", "pinch_position", "pinch_cited",
                "providers", "evidence_quote", "citations"):
        assert key in d
    assert isinstance(d["pinch_present"], bool)
    # providers are canonicalized (Pinch stays "Pinch", list of names)
    present = next(x for x in details if x["pinch_present"])
    assert "Pinch" in present["providers"]
    assert "Glow MedSpa" in present["providers"]
