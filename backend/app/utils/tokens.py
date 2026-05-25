"""Token counting and cost calculation utilities.

Costs are per-1K tokens as of the model versions used in this project.
Update these when switching model versions.
"""

# Cost per 1,000 tokens (input, output) in USD
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {
        "input": 0.003,
        "output": 0.015,
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.001,
        "output": 0.005,
    },
}

# Fallback cost for unknown models
_FALLBACK_COST = {"input": 0.003, "output": 0.015}


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate the estimated API cost for a Claude call.

    Args:
        input_tokens: Number of input/prompt tokens.
        output_tokens: Number of output/completion tokens.
        model: Model identifier string.

    Returns:
        Estimated cost in USD, rounded to 6 decimal places.
    """
    costs = MODEL_COSTS.get(model, _FALLBACK_COST)
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]
    return round(input_cost + output_cost, 6)
