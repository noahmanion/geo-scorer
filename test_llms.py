"""
test_llms.py - verify the unified interface works for all 4 models.
"""

from geo.llms import generate, ALL_MODELS

PROMPT = (
    "I'm building an agent thatneeds to fetch and parse arbitrary "
    "websites at runtime. What API should i use to convert page "
    "into clean markdown for context?"
)

total_cost = 0.0
for model in ALL_MODELS:
    try:
        r=generate(model, PROMPT,max_tokens=200)
        print(f"\n=== {model.upper()} ====")
        print(f" tokens: {r.input_tokens} in, {r.output_tokens} out")
        print(f" cost: ${r.cost_usd:.4f}")
        print(f" text: {r.text[:200]}...")
        total_cost += r.cost_usd
    except Exception as e:
        print(f"\n=== {model.upper()}: FAILED ===")
        print(f" {type(e).__name__}: {e}")

print(f"\nTOTAL COST: ${total_cost:.4f}")