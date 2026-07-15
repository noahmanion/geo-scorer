import pytest

from geo import llms
from geo.llms import Response


def _make_response(model, text):
    return Response(
        model=model,
        text=text,
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.0,
        citations=[],
        raw=None,
    )


def test_generate_raises_on_empty_grounded_text(monkeypatch):
    monkeypatch.setattr(
        llms, "_perplexity", lambda prompt, max_tokens=400: _make_response("perplexity", "   ")
    )
    with pytest.raises(RuntimeError, match="perplexity"):
        llms.generate("perplexity", "x")


def test_generate_passes_through_non_empty_text(monkeypatch):
    monkeypatch.setattr(
        llms, "_perplexity", lambda prompt, max_tokens=400: _make_response("perplexity", "hello world")
    )
    response = llms.generate("perplexity", "x")
    assert response.text == "hello world"


def test_looks_like_domain_accepts_bare_hosts():
    assert llms._looks_like_domain("bookpinch.com")
    assert llms._looks_like_domain("www.kbaestheticschicago.com")
    assert llms._looks_like_domain("Sub.Example.CO.UK")


def test_looks_like_domain_rejects_non_domains():
    # Gemini redirect URLs, page titles, and empties must NOT be treated as domains
    assert not llms._looks_like_domain("https://vertexaisearch.cloud.google.com/x")
    assert not llms._looks_like_domain("Pinch | At-Home Med Spa")
    assert not llms._looks_like_domain("")
    assert not llms._looks_like_domain("no-tld")
