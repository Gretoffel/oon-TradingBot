"""
Unit tests for core.parsing

Functions tested:
    - clean_amount
    - calculate_fee
    - extract_json_list
"""

import pytest

from core.parsing import (
    calculate_fee,
    clean_amount,
    extract_json_list,
)


# =========================================================================
# clean_amount
# =========================================================================

class TestCleanAmount:
    """Tests for clean_amount() - European number format parser."""

    def test_simple_integer(self):
        assert clean_amount("100") == 100.0

    def test_german_decimal(self):
        assert clean_amount("1.200,50") == 1200.50

    def test_comma_decimal_only(self):
        assert clean_amount("99,99") == 99.99

    def test_dot_decimal_only(self):
        assert clean_amount("99.99") == 99.99

    def test_currency_symbol_stripped(self):
        assert clean_amount("1.200,50 \u20ac") == 1200.50

    def test_negative_value(self):
        assert clean_amount("-50,00") == -50.0

    def test_plus_prefix(self):
        assert clean_amount("+12,34%") == 12.34

    def test_empty_string(self):
        assert clean_amount("") == 0.0

    def test_none_input(self):
        assert clean_amount(None) == 0.0

    def test_non_numeric_garbage(self):
        assert clean_amount("abc") == 0.0

    def test_integer_input(self):
        """Handles non-string input via str() cast."""
        assert clean_amount(42) == 42.0

    def test_large_german_number(self):
        assert clean_amount("1.234.567,89") == 1234567.89

    def test_whitespace_only(self):
        assert clean_amount("   ") == 0.0

    def test_zero(self):
        assert clean_amount("0") == 0.0

    def test_zero_with_decimals(self):
        assert clean_amount("0,00") == 0.0


# =========================================================================
# calculate_fee
# =========================================================================

class TestCalculateFee:
    """Tests for calculate_fee() - OON transaction fee calculator."""

    def test_zero_amount(self):
        assert calculate_fee(0) == 0.0

    def test_negative_amount(self):
        assert calculate_fee(-100) == 0.0

    def test_minimum_fee_applies(self):
        """Small amounts should hit the 17 EUR minimum base fee."""
        assert calculate_fee(1000) == 17.0 + 3.0

    def test_percentage_fee_applies(self):
        """Large amounts should use the 0.25% rate."""
        assert calculate_fee(10000) == 25.0 + 3.0

    def test_breakeven_point(self):
        """At 6800 EUR, 0.25% = 17, which equals the minimum."""
        assert calculate_fee(6800) == 17.0 + 3.0

    def test_just_above_breakeven(self):
        """Just above the breakeven: percentage fee > minimum."""
        result = calculate_fee(7000)
        expected = 7000 * 0.0025 + 3.0
        assert result == expected

    def test_fee_always_includes_flat(self):
        """Every non-zero trade has the 3 EUR flat surcharge."""
        assert calculate_fee(100) >= 3.0

    def test_very_small_amount(self):
        """Even 1 EUR trade gets minimum fee."""
        assert calculate_fee(1) == 20.0


# =========================================================================
# extract_json_list
# =========================================================================

class TestExtractJsonList:
    """Tests for extract_json_list() - JSON extraction from AI responses."""

    def test_clean_json(self):
        text = '[{"action": "BUY"}, {"action": "SELL"}]'
        result = extract_json_list(text)
        assert len(result) == 2
        assert result[0]["action"] == "BUY"

    def test_json_with_markdown_fences(self):
        text = '```json\n[{"a": 1}]\n```'
        result = extract_json_list(text)
        assert result == [{"a": 1}]

    def test_json_embedded_in_text(self):
        text = 'Here is the analysis:\n[{"isin": "US123"}]\nEnd of response.'
        result = extract_json_list(text)
        assert result[0]["isin"] == "US123"

    def test_empty_string(self):
        assert extract_json_list("") is None

    def test_none_input(self):
        assert extract_json_list(None) is None

    def test_no_json_in_text(self):
        assert extract_json_list("No JSON here at all.") is None

    def test_malformed_json(self):
        assert extract_json_list("[{broken json}]") is None

    def test_empty_list(self):
        result = extract_json_list("[]")
        assert result == []

    def test_footnote_references_stripped(self):
        """[1], [2] etc. from AI footnotes should not break parsing."""
        text = 'Result[1]:\n[{"stock": "AAPL"}]'
        result = extract_json_list(text)
        assert result[0]["stock"] == "AAPL"

    def test_nested_objects(self):
        text = '[{"data": {"nested": true}}]'
        result = extract_json_list(text)
        assert result[0]["data"]["nested"] is True
