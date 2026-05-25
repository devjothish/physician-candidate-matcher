"""Unit tests for token counting and cost calculation."""

import pytest

from app.utils.tokens import MODEL_COSTS, calculate_cost


class TestCostCalculation:
    """Tests for the calculate_cost utility."""

    def test_sonnet_cost(self) -> None:
        """Sonnet cost should match published rates."""
        # 1000 input tokens + 500 output tokens
        cost = calculate_cost(1000, 500, "claude-sonnet-4-20250514")
        # (1000/1000 * 0.003) + (500/1000 * 0.015) = 0.003 + 0.0075 = 0.0105
        assert cost == 0.0105

    def test_haiku_cost(self) -> None:
        """Haiku cost should be lower than Sonnet."""
        cost = calculate_cost(1000, 500, "claude-haiku-4-5-20251001")
        # (1000/1000 * 0.001) + (500/1000 * 0.005) = 0.001 + 0.0025 = 0.0035
        assert cost == 0.0035

    def test_haiku_cheaper_than_sonnet(self) -> None:
        """Haiku should always be cheaper than Sonnet for same token count."""
        haiku_cost = calculate_cost(5000, 2000, "claude-haiku-4-5-20251001")
        sonnet_cost = calculate_cost(5000, 2000, "claude-sonnet-4-20250514")
        assert haiku_cost < sonnet_cost

    def test_zero_tokens(self) -> None:
        """Zero tokens should produce zero cost."""
        cost = calculate_cost(0, 0, "claude-sonnet-4-20250514")
        assert cost == 0.0

    def test_large_token_count(self) -> None:
        """Large token counts should scale linearly."""
        small = calculate_cost(1000, 500, "claude-sonnet-4-20250514")
        large = calculate_cost(10000, 5000, "claude-sonnet-4-20250514")
        assert abs(large - small * 10) < 0.000001

    def test_unknown_model_uses_fallback(self) -> None:
        """Unknown model should use fallback costs (Sonnet rates)."""
        known = calculate_cost(1000, 500, "claude-sonnet-4-20250514")
        unknown = calculate_cost(1000, 500, "claude-unknown-model")
        assert unknown == known

    def test_output_tokens_more_expensive(self) -> None:
        """Output tokens should cost more than input tokens."""
        input_only = calculate_cost(1000, 0, "claude-sonnet-4-20250514")
        output_only = calculate_cost(0, 1000, "claude-sonnet-4-20250514")
        assert output_only > input_only

    def test_cost_rounding(self) -> None:
        """Cost should be rounded to 6 decimal places."""
        cost = calculate_cost(333, 777, "claude-sonnet-4-20250514")
        decimal_places = len(str(cost).split(".")[-1]) if "." in str(cost) else 0
        assert decimal_places <= 6

    def test_model_costs_dict_structure(self) -> None:
        """MODEL_COSTS should have input and output keys for each model."""
        for model_name, costs in MODEL_COSTS.items():
            assert "input" in costs, f"{model_name} missing 'input' cost"
            assert "output" in costs, f"{model_name} missing 'output' cost"
            assert costs["input"] > 0, f"{model_name} input cost must be positive"
            assert costs["output"] > 0, f"{model_name} output cost must be positive"
