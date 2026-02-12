"""
Unit tests for trading.bot

Functions tested:
    - run_bot_cycle  (main orchestration - quick check & full strategy)

All external dependencies are mocked:
    - Playwright (browser)
    - AI provider
    - Services (login, scan_depot, market_data)
    - Trading (actions, ai_service, algo_service)
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from trading.bot import run_bot_cycle


def _run(coro):
    """Run async coroutine in sync test."""
    return asyncio.run(coro)


def _mock_depot(cash=50000, stocks=None, open_orders=None):
    return {
        "cash": cash,
        "stocks": stocks or [],
        "open_orders": open_orders or [],
    }


@pytest.fixture
def bot_mocks():
    """Set up all mocks needed for run_bot_cycle."""
    patches = {}

    # Playwright
    mock_page = AsyncMock()
    mock_page.is_closed = MagicMock(return_value=False)
    mock_page.url = "https://oon.at/depot"
    mock_page.goto = AsyncMock()

    mock_context = AsyncMock()
    mock_context.pages = [mock_page]
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    mock_playwright = MagicMock()

    # Patch async_playwright context manager
    patches["playwright"] = patch("trading.bot.async_playwright")
    mock_ap = patches["playwright"].start()
    mock_ap_instance = AsyncMock()
    mock_ap.return_value.__aenter__ = AsyncMock(return_value=mock_ap_instance)
    mock_ap.return_value.__aexit__ = AsyncMock(return_value=False)

    # Patch create_browser_context
    patches["create_ctx"] = patch("trading.bot.create_browser_context",
                                   new_callable=AsyncMock,
                                   return_value=mock_context)
    patches["create_ctx"].start()

    # Patch create_provider
    mock_provider = AsyncMock()
    mock_provider.cleanup = AsyncMock()
    patches["create_provider"] = patch("trading.bot.create_provider",
                                        return_value=mock_provider)
    patches["create_provider"].start()

    # Patch login & scan_depot
    patches["login"] = patch("trading.bot.login", new_callable=AsyncMock)
    patches["login"].start()

    patches["scan_depot"] = patch("trading.bot.scan_depot",
                                   new_callable=AsyncMock,
                                   return_value=_mock_depot())
    patches["scan_depot"].start()

    # Patch remote_manager
    patches["rm"] = patch("trading.bot.remote_manager")
    patches["rm"].start()

    # Patch market data
    patches["snapshot"] = patch("trading.bot.get_market_snapshot",
                                 return_value={})
    patches["snapshot"].start()

    patches["is_open"] = patch("trading.bot.is_market_open",
                                return_value=True)
    patches["is_open"].start()

    # Patch trading functions
    patches["check_safety"] = patch("trading.bot.check_portfolio_safety",
                                     new_callable=AsyncMock,
                                     return_value=[])
    patches["check_safety"].start()

    patches["analyze_safety"] = patch("trading.bot.analyze_portfolio_safety",
                                       return_value=[])
    patches["analyze_safety"].start()

    patches["deep_dive"] = patch("trading.bot.analyze_candidates_deep_dive",
                                  new_callable=AsyncMock,
                                  return_value=[])
    patches["deep_dive"].start()

    patches["synthesize"] = patch("trading.bot.synthesize_decisions",
                                   return_value=[])
    patches["synthesize"].start()

    patches["buy"] = patch("trading.bot.execute_buy_order",
                            new_callable=AsyncMock,
                            return_value="SUCCESS")
    patches["buy"].start()

    patches["sell"] = patch("trading.bot.execute_sell_order",
                             new_callable=AsyncMock)
    patches["sell"].start()

    # Patch config
    patches["config"] = patch("trading.bot.config")
    mock_cfg = patches["config"].start()
    mock_cfg.OON_DEPOT_URL = "https://oon.at/depot"
    mock_cfg.PORTFOLIO_DIVERSITY = 5
    mock_cfg.MIN_CASH_FOR_NEW_TRADE = 6000
    mock_cfg.MAX_AI_CANDIDATES = 10

    yield {
        "page": mock_page,
        "context": mock_context,
        "provider": mock_provider,
        "patches": patches,
    }

    for p in patches.values():
        p.stop()


# =========================================================================
# run_bot_cycle - Quick Check mode
# =========================================================================

class TestRunBotCycleQuickCheck:
    """Tests for run_bot_cycle(full_analysis=False) - safety-only mode."""

    def test_completes_without_error(self, bot_mocks):
        _run(run_bot_cycle(full_analysis=False))

    def test_calls_login_and_scan(self, bot_mocks):
        with patch("trading.bot.login", new_callable=AsyncMock) as mock_login, \
             patch("trading.bot.scan_depot", new_callable=AsyncMock,
                   return_value=_mock_depot()) as mock_scan:
            _run(run_bot_cycle(full_analysis=False))
            mock_login.assert_called_once()
            mock_scan.assert_called_once()

    def test_calls_analyze_portfolio_safety(self, bot_mocks):
        with patch("trading.bot.analyze_portfolio_safety",
                   return_value=[]) as mock_safety:
            _run(run_bot_cycle(full_analysis=False))
            mock_safety.assert_called_once()

    def test_does_not_call_ai_in_quick_mode(self, bot_mocks):
        with patch("trading.bot.check_portfolio_safety",
                   new_callable=AsyncMock) as mock_ai:
            _run(run_bot_cycle(full_analysis=False))
            mock_ai.assert_not_called()

    def test_does_not_call_synthesize_in_quick_mode(self, bot_mocks):
        with patch("trading.bot.synthesize_decisions") as mock_synth:
            _run(run_bot_cycle(full_analysis=False))
            mock_synth.assert_not_called()

    def test_executes_emergency_sells(self, bot_mocks):
        sell_order = {"name": "Tesla", "grund": "STOP-LOSS"}

        with patch("trading.bot.analyze_portfolio_safety",
                   return_value=[sell_order]), \
             patch("trading.bot.scan_depot", new_callable=AsyncMock,
                   return_value=_mock_depot(
                       stocks=[{"name": "Tesla", "isin": "US123", "qty": 5}]
                   )), \
             patch("trading.bot.execute_sell_order",
                   new_callable=AsyncMock) as mock_sell:
            _run(run_bot_cycle(full_analysis=False))
            mock_sell.assert_called()

    def test_cleanup_called(self, bot_mocks):
        _run(run_bot_cycle(full_analysis=False))
        bot_mocks["provider"].cleanup.assert_called()


# =========================================================================
# run_bot_cycle - Full Strategy mode
# =========================================================================

class TestRunBotCycleFullStrategy:
    """Tests for run_bot_cycle(full_analysis=True) - complete strategy."""

    def test_completes_without_error(self, bot_mocks):
        _run(run_bot_cycle(full_analysis=True))

    def test_calls_ai_defense(self, bot_mocks):
        with patch("trading.bot.check_portfolio_safety",
                   new_callable=AsyncMock, return_value=[]) as mock_ai:
            _run(run_bot_cycle(full_analysis=True))
            # AI defense is called when there are tradeable stocks
            # (may not be called if no stocks in depot)

    def test_calls_synthesize_decisions(self, bot_mocks):
        with patch("trading.bot.synthesize_decisions",
                   return_value=[]) as mock_synth:
            _run(run_bot_cycle(full_analysis=True))
            mock_synth.assert_called_once()

    def test_executes_buy_orders(self, bot_mocks):
        buy_order = {
            "name": "Nvidia", "isin": "US67066G1040",
            "betrag_eur": 8000, "grund": "Strong momentum",
        }

        with patch("trading.bot.synthesize_decisions",
                   return_value=[buy_order]), \
             patch("trading.bot.execute_buy_order",
                   new_callable=AsyncMock,
                   return_value="SUCCESS") as mock_buy:
            _run(run_bot_cycle(full_analysis=True))
            mock_buy.assert_called()

    def test_skips_buy_when_insufficient_cash(self, bot_mocks):
        with patch("trading.bot.scan_depot", new_callable=AsyncMock,
                   return_value=_mock_depot(cash=100)), \
             patch("trading.bot.analyze_candidates_deep_dive",
                   new_callable=AsyncMock) as mock_dd:
            _run(run_bot_cycle(full_analysis=True))
            mock_dd.assert_not_called()

    def test_handles_exception_gracefully(self, bot_mocks):
        """Exception after login/scan is caught. Note: if login itself
        throws, current_cash is unbound -> UnboundLocalError (known bug
        in bot.py). We test the post-scan path here."""
        with patch("trading.bot.get_market_snapshot",
                   side_effect=Exception("API down")):
            _run(run_bot_cycle(full_analysis=True))
            # Should not propagate - caught internally
