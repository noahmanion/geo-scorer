"""Pure config loaders and cell expansion for the Pinch GEO run."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlparse


def load_cities(path: str = "cities.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def load_queries(path: str = "queries.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def load_brand(path: str = "brand.json") -> dict:
    return json.loads(Path(path).read_text())


def expand_cells(cities: list[dict], queries: list[dict]) -> list[dict]:
    """Cross cities × queries into concrete prompts.

    `{city}` in a template is replaced with "Name, ST".
    """
    cells: list[dict] = []
    for city in cities:
        label = f"{city['name']}, {city['state']}"
        for q in queries:
            cells.append({
                "city": city["name"],
                "state": city["state"],
                "query_id": q["id"],
                "segment": q["segment"],
                "prompt": q["template"].replace("{city}", label),
            })
    return cells


def brand_domain_cited(domain: str, citations: list[str]) -> bool:
    """True if `domain` is the host of any citation URL.

    Ignores a leading `www.`, is case-insensitive, and ignores path.
    """
    target = domain.lower().removeprefix("www.")
    for url in citations or []:
        host = (urlparse(url).netloc or "").lower().removeprefix("www.")
        if host == target:
            return True
    return False
