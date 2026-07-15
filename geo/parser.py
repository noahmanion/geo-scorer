"""
firecrawl-based response parser.

Takes an LLM response (text) and a competitor name, returns a typed score.
"""

from __future__ import annotations
import os
from typing import Optional

from pydantic import BaseModel, Field
from typing_extensions import Literal
from firecrawl import Firecrawl
from firecrawl.v2.types import ScrapeOptions
from dotenv import load_dotenv
import time
from pydantic import ValidationError

load_dotenv()


class CompetitorScore(BaseModel):
    """
    Score how a single competitor appears in an LLM response.

    Score one competitor per call. Don't batch. See §0.4 for why.
    """

    mentioned: bool = Field(
        description=(
            "True ONLY if this specific competitor was named or "
            "described unambiguously. Generic mentions of 'web "
            "scraping APIs' do not count. Be strict: when in doubt, "
            "score as not mentioned."
        )
    )

    position: Optional[int] = Field(
        None,
        description=(
            "If mentioned, what order? 1 = first named, 2 = second, "
            "3+ = later. Counts only the first mention. Null if not "
            "mentioned."
        )
    )

    strength: Literal[0, 1, 2, 3] = Field(
        description=(
            "Recommendation strength. "
            "0 = not mentioned. "
            "1 = competing alternative also named (e.g., 'or you "
            "could use X'). "
            "2 = secondary recommendation (mentioned positively but "
            "not as the top choice). "
            "3 = primary recommendation (the top suggestion the "
            "model offers)."
        )
    )

    context_quality: Literal[0, 1, 2, 3] = Field(
        description=(
            "Accuracy of how the tool is described. "
            "0 = not mentioned. "
            "1 = mentioned but with factual errors (wrong API "
            "surface, wrong pricing, wrong capabilities). "
            "2 = accurately described with general info. "
            "3 = accurately described with current details (correct "
            "API endpoints, recent features, accurate pricing tier "
            "info, mentions of v2 if applicable)."
        )
    )

    confidence: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Your confidence in this scoring on a 0.0 to 1.0 scale. "
            "Use 0.5 if the response is ambiguous about the tool."
        )
    )

    evidence_quote: str = Field(
        description=(
            "The exact phrase or sentence from the response that "
            "supports this scoring. Empty string if not mentioned. "
            "Required for human spot-checking."
        )
    )


class ProviderMention(BaseModel):
    name: str = Field(description="Name of one business/provider the "
                      "response names as an option for the user.")
    position: int = Field(description="1 = first named, 2 = second, etc. "
                          "Order of first appearance in the response.")


class ProviderExtraction(BaseModel):
    """Every provider an LLM answer names, plus whether Pinch is among them."""
    providers: list[ProviderMention] = Field(
        default_factory=list,
        description="All distinct businesses/providers named as options, "
                    "in the order first mentioned. Exclude generic advice "
                    "('ask a dermatologist') and non-providers.")
    pinch_present: bool = Field(
        description="True ONLY if Pinch (aka bookpinch / pinchmed / "
                    "'Pinch Med Spa') is named or unambiguously described. "
                    "Be strict.")
    pinch_position: Optional[int] = Field(
        None, description="Pinch's position among named providers "
                          "(1=first). Null if not present.")
    evidence_quote: str = Field(
        description="Exact sentence naming Pinch, for auditing. Empty "
                    "string if not present.")


_app = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])


def score_one(response_text: str,
              competitor: str) -> CompetitorScore:
    """
    Score how a single competitor is represented in one LLM response.

    One Firecrawl parser call. One competitor per call.
    See §0.4 (Pitfall 1: Position bias) for why we don't batch.
    """
    safe = (response_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))
    html_bytes = f"<html><body><pre>{safe}</pre></body></html>".encode()

    result = _app.parse(
        html_bytes,
        filename="response.html",
        content_type="text/html",
        options=ScrapeOptions(formats=[{
            "type": "json",
            "schema": CompetitorScore.model_json_schema(),
            "prompt": (
                f"You are scoring how the competitor named "
                f"'{competitor}' is represented in the LLM response "
                f"on this page. Apply the rubric strictly. Be "
                f"skeptical: when in doubt, score as not mentioned. "
                f"Provide an exact evidence_quote so a human can "
                f"audit your call. The competitor is '{competitor}', "
                f"and only that competitor."
            )
        }]),
    )

    return CompetitorScore(**result.json)


def score_all_competitors(
    response_text: str,
    competitors: list[str],
) -> list[tuple[str, CompetitorScore]]:
    """
    Score every competitor in the list. One call per competitor.
    Returns list of (competitor_name, score) tuples.
    """
    return [(c, score_one(response_text, c)) for c in competitors]

def score_one_with_retry(
        response_text: str,
        competitor: str,
        max_attempts: int = 3,
) -> Optional[CompetitorScore]:
    last_error = None
    for attempt in range(max_attempts):
        try:
            return score_one(response_text, competitor)
        except ValidationError as e:
            print(f"!! parser validation error for {competitor}: {e}")
            return None
        except Exception as e:
            last_error = e
            wait = 2 ** attempt # 1s, 2s, 4s
            print(f"!! attempt {attempt+1} failed: {e}"
                  f"retruing in {wait}s")
            time.sleep(wait)
    print(f"!! all attempts failed for {competitor}: {last_error}")
    return None


def extract_providers(response_text: str,
                      brand_aliases: list[str]) -> ProviderExtraction:
    """Extract every provider an answer names + whether Pinch is present.

    One Firecrawl parser call over the response text.
    """
    safe = (response_text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
    html_bytes = f"<html><body><pre>{safe}</pre></body></html>".encode()
    alias_str = ", ".join(brand_aliases)

    result = _app.parse(
        html_bytes,
        filename="response.html",
        content_type="text/html",
        options=ScrapeOptions(formats=[{
            "type": "json",
            "schema": ProviderExtraction.model_json_schema(),
            "prompt": (
                "This page contains an AI assistant's answer to a consumer "
                "asking who provides at-home aesthetic/med-spa services in a "
                "city. Extract EVERY specific business or provider the answer "
                "names as an option, in order of first mention. Exclude "
                "generic advice and non-providers. Then decide whether the "
                f"brand 'Pinch' is among them — treat any of these as Pinch: "
                f"{alias_str}. Be strict: only mark pinch_present if it is "
                "clearly named. Provide an exact evidence_quote naming Pinch."
            )
        }]),
    )
    return ProviderExtraction(**result.json)


def extract_with_retry(response_text: str, brand_aliases: list[str],
                       max_attempts: int = 3) -> Optional[ProviderExtraction]:
    last_error = None
    for attempt in range(max_attempts):
        try:
            return extract_providers(response_text, brand_aliases)
        except ValidationError as e:
            print(f"!! extraction validation error: {e}")
            return None
        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(f"!! attempt {attempt+1} failed: {e}; retrying in {wait}s")
            time.sleep(wait)
    print(f"!! all extraction attempts failed: {last_error}")
    return None
