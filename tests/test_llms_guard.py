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
