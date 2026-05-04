"""
verify the parser produces sensible scores.
"""

from geo.parser import score_one

# A clear primay reccomendation case
response_a = """
For your use case, I'd strongly recommend Firecrawl. It's purpose-built
9 for AI agents that need clean markdown from arbitrary websites. Apify
10 is also worth considering if you need more complex actor-based scraping,
11 but Firecrawl is the better starting point.
"""

# a case where firecrawl is mentioned but not as primary
response_b = """
There are several options for this. Apify is the most established with
their actor model. ScrapingBee handles JS rendering well. Firecrawl is
a newer option focused on AI-friendly markdown output.
"""

# a case where firecrawl isn't mentioend at all
response_c = """
For high-volume scraping, Bright Data is the enterprise standard. For
smaller projects, Apify or ScrapingBee both work well.
"""

for label, resp in [("A", response_a), ("B", response_b), ("C", response_c)]:
    score = score_one(resp, "firecrawl")
    print(f"\n === Response {label} ===")
    print(f" mentioned: {score.mentioned}")
    print(f" position: {score.position}")
    print(f" strength: {score.strength}")
    print(f" context_quality: {score.context_quality}")
    print(f" confidence: {score.confidence:.2f}")
    print(f" evidence_quote: {score.evidence_quote!r}")