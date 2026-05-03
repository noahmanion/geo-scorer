"""
first contat
"""
import os
from dotenv import load_dotenv
from firecrawl import Firecrawl
from pydantic import BaseModel, Field
from typing import List
import urllib.parse

load_dotenv()

app = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

class FirecrawlInfo(BaseModel):
    """Schemea describing what was extracted from firecrawl.dev"""
    company_mission: str = Field(
        description="The company's state mission or value proposition"
    )
    is_open_source: bool = Field(
        description="is the project open source?"
    )
    main_features: List[str] = Field(
        description="The main product features listed on the page"
    )

## Scrape a single URL and get markdown back
result = app.scrape(
"https://firecrawl.dev",
formats=[{
    "type": "json",
    "schema": FirecrawlInfo.model_json_schema(),
    }],
)

## the striuctured data is in result.json
data = FirecrawlInfo(**result.json)
print(f"Mission: {data.company_mission}")
print(f"Open Source: {data.is_open_source}")
print(f"Features:")
for f in data.main_features:
    print(f"  - {f}")


search_result = app.search(
    "best web scraping API for AI agents",
    limit=3
)

for hit in search_result.web:
    print(f"{hit.title}")
    print(f"{hit.url}")
    print(f" {hit.description[:120]}")
    print()

def text_to_data_url(text: str) -> str:
    """
    Wrap arbitrary text as a dat: URL so any scraper can read it.
    No server, no tempfiles. just URL encodewd HTML
    """
    html = f"<html><body><pre>{text}</pre></body></html>"
    encoded = urllib.parse.quote(html)
    return f"data:text/html;charset=utf-8,{encoded}"

## Try it: take an llm-style response and parse it.
fake_llm_response = """
For your agent that needs to scrape websites, I'd recommend Firecrawl
as the primary option. Apify is a strong alternative if you need more
complex browser automation, and Browserbase is worth considering if
you need fine-grained control over the headless browser.
"""

url = text_to_data_url(fake_llm_response)
print(f"data: URL is {len(url)} chars long")
print(f"first 80 chars: {url[:80]}")

## Now scrape THAT
class ToolMention(BaseModel):
    tool_name: str = Field(description="Name of a tool mentioned")
    role: str = Field(
    description="primary | alternative | mentioned"
    )
class Mentions(BaseModel):
    tools: List[ToolMention]

result = app.scrape(
    url,
    formats=[{
        "type": "json",
        "schema": Mentions.model_json_schema(),
        "prompt": "Extract every tool mentioned and what role it plays.",
    }],
)

data = Mentions(**result.json)
for tool in data.tools:
    print(f"{tool.tool_names}: ({tool.role})")