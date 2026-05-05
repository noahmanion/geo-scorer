"""
unified interface for Anthropic, OpenAI, Google & Perplexity
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

from anthropic import Anthropic
from openai import OpenAI
from google import genai
from google.genai import types as genai_types
import httpx

load_dotenv()

ModelName = Literal["claude", "gpt", "gemini", "perplexity"]


@dataclass
class Response:
    ## One LLM response, normalized across providers
    model: ModelName
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    raw: object ## original SDK response, for debugging

# ---- pricing per million tokens (input, output) ----
# Update these when prices change.
PRICING = {
"claude": (3.00, 15.00), # claude-opus-4-7
"gpt": (1.75, 14.00), # gpt-5.5
"gemini": (0.30, 2.50), # gemini-2.5-flash
"perplexity": (1.00, 1.00), # sonar-pro (illustrative)
}

def _calc_cost(model: ModelName, input_tokens: int, output_tokens: int) -> float:
    ## Cost in USD given pricing per million tokens
    in_rate, out_rate = PRICING[model]
    return (input_tokens / 1000000) * in_rate + \
    (output_tokens / 1000000) * out_rate


"""
Claude Adapter
"""

_anthropic = Anthropic()

def _claude(prompt: str, max_tokens: int = 400) -> Response:
    msg = _anthropic.messages.create(
        model="claude-opus-4-7",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    return Response(
        model="claude",
        text=text,
        input_tokens=msg.usage.input_tokens,
        output_tokens=msg.usage.output_tokens,
        cost_usd=_calc_cost("claude", msg.usage.input_tokens, msg.usage.output_tokens),
        raw=msg,
    )

"""
OpenAI Adapter
"""

_openai = OpenAI()

def _gpt(prompt: str, max_tokens: int = 400) -> Response:
    resp = _openai.chat.completions.create(
        model="gpt-5.5",
        max_completion_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content or ""
    return Response(
        model="gpt",
        text=text,
        input_tokens=resp.usage.prompt_tokens,
        output_tokens=resp.usage.completion_tokens,
        cost_usd=_calc_cost("gpt", resp.usage.prompt_tokens, resp.usage.completion_tokens),
        raw=resp,
    )

"""
Google Adapter
""" 

_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _gemini_call(prompt: str, max_tokens: int = 400) -> Response:
    resp=_gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
        ),

    )
    text = resp.text or ""

    ## Gemini reports tokens via usage_metadata.
    usage = resp.usage_metadata
    return Response(
        model="gemini",
        text=text,
        input_tokens=usage.prompt_token_count or 0,
        output_tokens=usage.candidates_token_count or 0,
        cost_usd=_calc_cost(
            "gemini", 
            usage.prompt_token_count or 0,
            usage.candidates_token_count or 0,
        ),
        raw=resp,
    )

"""
Perplexity Adapter
"""

def _perplexity(prompt: str, max_tokens: int = 400) -> Response:
    r = httpx.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
        },
        json={
            "model": "sonar-pro",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()

    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return Response(
        model="perplexity",
        text=text,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        cost_usd=_calc_cost(
            "perplexity", 
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        ),
        raw=data,
    )
def generate(model: ModelName, prompt: str, max_tokens: int = 400) -> Response:
    if model == "claude":
        return _claude(prompt, max_tokens)
    elif model == "gpt":
        return _gpt(prompt, max_tokens)
    elif model == "gemini":
        return _gemini_call(prompt, max_tokens)
    elif model == "perplexity":
        return _perplexity(prompt, max_tokens)
    else:
        raise ValueError(f"Unknown model: {model}")

ALL_MODELS: list[ModelName] = ["claude", "gpt", "gemini", "perplexity"]
