"""
Unit tests for trading.ai_service

Functions tested:
    - check_portfolio_safety      (AI defense prompt & response parsing)
    - analyze_candidates_deep_dive (AI deep-dive prompt & response parsing)

The AI provider is mocked - no actual API calls are made.
"""

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trading.ai_service import check_portfolio_safety, analyze_candidates_deep_dive


def _run(coro):
    """Run async coroutine in sync test."""
    return asyncio.run(coro)


@pytest.fixture
def mock_provider():
    """Create a mock AI provider with async send_prompt."""
    provider = AsyncMock()
    provider.send_prompt = AsyncMock(return_value=None)
    return provider


# =========================================================================
# check_portfolio_safety
# =========================================================================

class TestCheckPortfolioSafety:
    """Tests for check_portfolio_safety() - AI defense phase."""

    def test_empty_stocks_returns_empty(self, mock_provider):
        result = _run(check_portfolio_safety(mock_provider, []))
        assert result == {}

    def test_none_stocks_returns_empty(self, mock_provider):
        result = _run(check_portfolio_safety(mock_provider, None))
        assert result == {}

    def test_sends_prompt_to_provider(self, mock_provider):
        stocks = [{"name": "Tesla", "isin": "US88160R1014"}]
        mock_provider.send_prompt = AsyncMock(return_value="[]")
        _run(check_portfolio_safety(mock_provider, stocks))
        mock_provider.send_prompt.assert_called_once()

    def test_prompt_contains_stock_names(self, mock_provider):
        stocks = [{"name": "Apple", "isin": "US0378331005"}]
        mock_provider.send_prompt = AsyncMock(return_value="[]")
        _run(check_portfolio_safety(mock_provider, stocks))
        prompt = mock_provider.send_prompt.call_args[0][0]
        assert "Apple" in prompt

    def test_parses_hold_response(self, mock_provider):
        stocks = [{"name": "Tesla", "isin": "US123"}]
        response = json.dumps([{"isin": "US123", "action": "HOLD"}])
        mock_provider.send_prompt = AsyncMock(return_value=response)
        result = _run(check_portfolio_safety(mock_provider, stocks))
        assert len(result) == 1
        assert result[0]["action"] == "HOLD"

    def test_parses_emergency_sell_response(self, mock_provider):
        stocks = [{"name": "Tesla", "isin": "US123"}]
        response = json.dumps([
            {"isin": "US123", "action": "EMERGENCY_SELL", "reason": "Fraud detected"}
        ])
        mock_provider.send_prompt = AsyncMock(return_value=response)
        result = _run(check_portfolio_safety(mock_provider, stocks))
        assert len(result) == 1
        assert result[0]["action"] == "EMERGENCY_SELL"

    def test_returns_empty_on_none_response(self, mock_provider):
        stocks = [{"name": "Tesla", "isin": "US123"}]
        mock_provider.send_prompt = AsyncMock(return_value=None)
        result = _run(check_portfolio_safety(mock_provider, stocks))
        assert result == []

    def test_returns_empty_on_garbage_response(self, mock_provider):
        stocks = [{"name": "Tesla", "isin": "US123"}]
        mock_provider.send_prompt = AsyncMock(return_value="No JSON here")
        result = _run(check_portfolio_safety(mock_provider, stocks))
        assert result == []

    def test_handles_markdown_fenced_response(self, mock_provider):
        stocks = [{"name": "Tesla", "isin": "US123"}]
        response = '```json\n[{"isin": "US123", "action": "HOLD"}]\n```'
        mock_provider.send_prompt = AsyncMock(return_value=response)
        result = _run(check_portfolio_safety(mock_provider, stocks))
        assert len(result) == 1

    def test_multiple_stocks(self, mock_provider):
        stocks = [
            {"name": "Tesla", "isin": "US123"},
            {"name": "Apple", "isin": "US456"},
        ]
        response = json.dumps([
            {"isin": "US123", "action": "HOLD"},
            {"isin": "US456", "action": "EMERGENCY_SELL", "reason": "Bad news"},
        ])
        mock_provider.send_prompt = AsyncMock(return_value=response)
        result = _run(check_portfolio_safety(mock_provider, stocks))
        assert len(result) == 2


# =========================================================================
# analyze_candidates_deep_dive
# =========================================================================

class TestAnalyzeCandidatesDeepDive:
    """Tests for analyze_candidates_deep_dive() - AI synthesis phase."""

    def test_empty_candidates_returns_empty(self, mock_provider):
        result = _run(analyze_candidates_deep_dive(mock_provider, []))
        assert result == []

    def test_none_candidates_returns_empty(self, mock_provider):
        result = _run(analyze_candidates_deep_dive(mock_provider, None))
        assert result == []

    def test_sends_prompt_to_provider(self, mock_provider):
        candidates = [{"isin": "US123", "ticker": "TSLA", "price": 150}]
        mock_provider.send_prompt = AsyncMock(return_value="[]")
        _run(analyze_candidates_deep_dive(mock_provider, candidates))
        mock_provider.send_prompt.assert_called_once()

    def test_prompt_contains_candidate_info(self, mock_provider):
        candidates = [{"isin": "US123", "ticker": "TSLA", "price": 150}]
        mock_provider.send_prompt = AsyncMock(return_value="[]")
        _run(analyze_candidates_deep_dive(mock_provider, candidates))
        prompt = mock_provider.send_prompt.call_args[0][0]
        assert "US123" in prompt
        assert "TSLA" in prompt

    def test_parses_valid_response(self, mock_provider):
        candidates = [{"isin": "US123", "ticker": "TSLA", "price": 150}]
        response = json.dumps([{
            "isin": "US123",
            "name": "TSLA",
            "earnings_date": "2026-04-15",
            "analyst_rating": 4.2,
            "news_sentiment": 3.8,
            "brief_summary": "Strong momentum"
        }])
        mock_provider.send_prompt = AsyncMock(return_value=response)
        result = _run(analyze_candidates_deep_dive(mock_provider, candidates))
        assert len(result) == 1
        assert result[0]["analyst_rating"] == 4.2

    def test_returns_empty_on_none_response(self, mock_provider):
        candidates = [{"isin": "US123", "ticker": "TSLA", "price": 150}]
        mock_provider.send_prompt = AsyncMock(return_value=None)
        result = _run(analyze_candidates_deep_dive(mock_provider, candidates))
        assert result == []

    def test_returns_empty_on_invalid_json(self, mock_provider):
        candidates = [{"isin": "US123", "ticker": "TSLA", "price": 150}]
        mock_provider.send_prompt = AsyncMock(return_value="Sorry, I can't do that")
        result = _run(analyze_candidates_deep_dive(mock_provider, candidates))
        assert result == []

    def test_multiple_candidates(self, mock_provider):
        candidates = [
            {"isin": "US123", "ticker": "TSLA", "price": 150},
            {"isin": "US456", "ticker": "AAPL", "price": 180},
        ]
        response = json.dumps([
            {"isin": "US123", "name": "TSLA", "earnings_date": "0",
             "analyst_rating": 4.0, "news_sentiment": 3.5, "brief_summary": "OK"},
            {"isin": "US456", "name": "AAPL", "earnings_date": "0",
             "analyst_rating": 4.5, "news_sentiment": 4.0, "brief_summary": "Strong"},
        ])
        mock_provider.send_prompt = AsyncMock(return_value=response)
        result = _run(analyze_candidates_deep_dive(mock_provider, candidates))
        assert len(result) == 2

    def test_handles_markdown_fenced_response(self, mock_provider):
        candidates = [{"isin": "US123", "ticker": "TSLA", "price": 150}]
        response = '```json\n[{"isin": "US123", "name": "TSLA", "earnings_date": "0", "analyst_rating": 4.0, "news_sentiment": 3.5, "brief_summary": "OK"}]\n```'
        mock_provider.send_prompt = AsyncMock(return_value=response)
        result = _run(analyze_candidates_deep_dive(mock_provider, candidates))
        assert len(result) == 1
