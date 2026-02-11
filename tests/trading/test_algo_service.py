"""
Unit tests for trading.algo_service

Functions tested:
    - analyze_portfolio_safety  (defense / sell logic)
    - synthesize_decisions      (buy decision logic)
    - calculate_algo_decisions  (stub - returns empty)

All external dependencies are mocked:
    - config values          -> monkeypatched to known constants
    - remote_manager         -> mocked (no file I/O)
    - is_market_open         -> mocked (always returns True unless specified)
    - get_minutes_until_close -> mocked (always returns 120 unless specified)

Complexity notes:
    - analyze_portfolio_safety: Very high cyclomatic complexity.
      6 sequential sell checks (AI, EOD, HWM, StopLoss, TakeProfit, Trailing,
      TrendBreak), each with its own conditions. One giant loop with 'continue'
      exits. We test each path individually via carefully crafted mock data.
"""

import pytest
from unittest.mock import MagicMock, patch

import trading.algo_service as algo


# =========================================================================
# Shared fixtures
# =========================================================================

@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    """Set all config values to known, predictable defaults."""
    monkeypatch.setattr(algo.config, "STOP_LOSS_HARD_PCT", -5.0)
    monkeypatch.setattr(algo.config, "TAKE_PROFIT_HARD_PCT", 20.0)
    monkeypatch.setattr(algo.config, "HWM_TRIGGER_PCT", 4.0)
    monkeypatch.setattr(algo.config, "HWM_DROP_THRESHOLD", 1.5)
    monkeypatch.setattr(algo.config, "MINUTES_BEFORE_CLOSE_TO_SELL", 0)
    monkeypatch.setattr(algo.config, "TRAILING_STOP_ACTIVATE_PCT", 1.0)
    monkeypatch.setattr(algo.config, "RSI_OVERBOUGHT", 85)
    monkeypatch.setattr(algo.config, "PORTFOLIO_DIVERSITY", 5)
    monkeypatch.setattr(algo.config, "MIN_CASH_FOR_NEW_TRADE", 6000)
    monkeypatch.setattr(algo.config, "MIN_FINAL_SCORE", 78)
    monkeypatch.setattr(algo.config, "TECH_WEIGHT", 0.5)
    monkeypatch.setattr(algo.config, "AI_WEIGHT", 0.5)
    monkeypatch.setattr(algo.config, "MAX_NEW_POSITIONS_PER_CYCLE", 3)
    monkeypatch.setattr(algo.config, "MIN_TRADE_VOLUME", 6000)
    monkeypatch.setattr(algo.config, "MAX_INVEST_PER_STOCK", 11500)
    monkeypatch.setattr(algo.config, "EARNINGS_DAYS_THRESHOLD", 1)


@pytest.fixture(autouse=True)
def mock_remote_manager(monkeypatch):
    """Mock remote_manager so no files are read/written."""
    monkeypatch.setattr(algo.remote_manager, "get_high_water_marks", lambda: {})
    monkeypatch.setattr(algo.remote_manager, "save_high_water_marks", lambda x: None)


@pytest.fixture(autouse=True)
def mock_market_funcs(monkeypatch):
    """Mock market functions to always return 'open' with plenty of time."""
    monkeypatch.setattr(algo, "is_market_open", lambda ticker: True)
    monkeypatch.setattr(algo, "get_minutes_until_close", lambda ticker: 120)


def _make_depot(stocks=None, cash=50000, open_orders=None):
    """Helper: build a minimal depot_data dict."""
    return {
        "cash": cash,
        "stocks": stocks or [],
        "open_orders": open_orders or [],
    }


def _make_stock(name="Tesla", isin="US123", perf="+2.00%", qty=5):
    return {"name": name, "isin": isin, "qty": qty, "performance_since_buy": perf}


def _make_tech(ticker="TSLA", isin="US123", price=150, rsi=60,
               ema_fast=145, ema_slow=140, trend="UP", tech_score=80):
    return {
        "ticker": ticker, "isin": isin, "price": price, "rsi": rsi,
        "ema_fast": ema_fast, "ema_slow": ema_slow, "trend": trend,
        "tech_score": tech_score, "volume_ratio": 1.5, "atr": 3.0,
    }


# =========================================================================
# analyze_portfolio_safety
# =========================================================================

class TestAnalyzePortfolioSafety:
    """Tests for analyze_portfolio_safety() - defense sell logic."""

    def test_no_stocks_returns_empty(self):
        depot = _make_depot(stocks=[])
        sells = algo.analyze_portfolio_safety(depot, [], {})
        assert sells == []

    def test_hold_when_everything_is_fine(self):
        """Stock with +2% perf, good RSI, good trend -> no sell."""
        depot = _make_depot(stocks=[_make_stock(perf="+2.00%")])
        snapshot = {"US123": _make_tech(rsi=60, price=150, ema_slow=140)}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert sells == []

    # --- C. STOP LOSS ---

    def test_stop_loss_triggers(self):
        """Performance below STOP_LOSS_HARD_PCT (-5%) -> SELL."""
        depot = _make_depot(stocks=[_make_stock(perf="-6.00%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1
        assert "STOP-LOSS" in sells[0]["grund"]

    def test_stop_loss_exact_boundary(self):
        """Performance exactly at stop loss threshold -> SELL."""
        depot = _make_depot(stocks=[_make_stock(perf="-5.00%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1

    # --- D. TAKE PROFIT ---

    def test_take_profit_triggers(self):
        """Performance above TAKE_PROFIT_HARD_PCT (20%) -> SELL."""
        depot = _make_depot(stocks=[_make_stock(perf="+21.00%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1
        assert "PROFIT" in sells[0]["grund"]

    # --- B. HIGH WATER MARK ---

    def test_hwm_trailing_stop_triggers(self, monkeypatch):
        """Stock peaked at 6%, now at 4% -> drawdown 2% >= threshold 1.5% -> SELL."""
        monkeypatch.setattr(algo.remote_manager, "get_high_water_marks",
                            lambda: {"US123": 6.0})
        depot = _make_depot(stocks=[_make_stock(perf="+4.00%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1
        assert "HWM-EXIT" in sells[0]["grund"]

    def test_hwm_no_trigger_within_threshold(self, monkeypatch):
        """Stock peaked at 5%, now at 4.5% -> drawdown 0.5% < 1.5% -> HOLD."""
        monkeypatch.setattr(algo.remote_manager, "get_high_water_marks",
                            lambda: {"US123": 5.0})
        depot = _make_depot(stocks=[_make_stock(perf="+4.50%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert sells == []

    def test_hwm_not_active_below_trigger(self, monkeypatch):
        """HWM only activates when peak >= HWM_TRIGGER_PCT (4%)."""
        monkeypatch.setattr(algo.remote_manager, "get_high_water_marks",
                            lambda: {"US123": 3.0})  # below 4% trigger
        depot = _make_depot(stocks=[_make_stock(perf="+1.00%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert sells == []

    # --- AI DEFENSE ---

    def test_ai_emergency_sell(self):
        """AI flags EMERGENCY_SELL -> SELL regardless of technicals."""
        depot = _make_depot(stocks=[_make_stock(perf="+5.00%")])
        ai_results = [{"isin": "US123", "action": "EMERGENCY_SELL", "reason": "Fraud"}]
        sells = algo.analyze_portfolio_safety(depot, ai_results, {})
        assert len(sells) == 1
        assert "AI" in sells[0]["grund"]

    def test_ai_hold_no_sell(self):
        """AI says HOLD -> should not trigger sell."""
        depot = _make_depot(stocks=[_make_stock(perf="+5.00%")])
        ai_results = [{"isin": "US123", "action": "HOLD"}]
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, ai_results, snapshot)
        assert sells == []

    # --- A. EOD PROTECTION ---

    def test_eod_sell_when_enabled(self, monkeypatch):
        """When MINUTES_BEFORE_CLOSE_TO_SELL > 0 and time is close -> SELL."""
        monkeypatch.setattr(algo.config, "MINUTES_BEFORE_CLOSE_TO_SELL", 30)
        monkeypatch.setattr(algo, "get_minutes_until_close", lambda t: 10)
        depot = _make_depot(stocks=[_make_stock(perf="+1.00%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1
        assert "EOD" in sells[0]["grund"]

    def test_eod_no_sell_when_disabled(self, monkeypatch):
        """MINUTES_BEFORE_CLOSE_TO_SELL=0 means EOD protection is off."""
        monkeypatch.setattr(algo.config, "MINUTES_BEFORE_CLOSE_TO_SELL", 0)
        depot = _make_depot(stocks=[_make_stock(perf="+1.00%")])
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert sells == []

    # --- E. RSI OVERBOUGHT ---

    def test_rsi_overbought_sell(self):
        """RSI > 85 while in profit >= trailing activate -> SELL."""
        depot = _make_depot(stocks=[_make_stock(perf="+2.00%")])
        snapshot = {"US123": _make_tech(rsi=90)}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1
        assert "OVERBOUGHT" in sells[0]["grund"]

    # --- E. EMA TRAILING STOP ---

    def test_ema_trailing_stop(self):
        """Price below EMA slow while in profit -> SELL."""
        depot = _make_depot(stocks=[_make_stock(perf="+2.00%")])
        snapshot = {"US123": _make_tech(price=130, ema_slow=140, rsi=60)}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1
        assert "T-STOP" in sells[0]["grund"]

    # --- F. TREND BREAK ---

    def test_trend_break_negative_perf(self):
        """Price below EMA slow AND negative perf -> SELL."""
        depot = _make_depot(stocks=[_make_stock(perf="-1.50%")])
        snapshot = {"US123": _make_tech(price=130, ema_slow=140, rsi=60)}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1
        assert "TREND" in sells[0]["grund"]

    # --- MARKET CLOSED ---

    def test_market_closed_wait_signal(self, monkeypatch):
        """When market is closed -> signal=WAIT, no sell."""
        monkeypatch.setattr(algo, "is_market_open", lambda t: False)
        depot = _make_depot(stocks=[_make_stock(perf="-6.00%")])  # would trigger stop loss
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert sells == []

    # --- SKIP PENDING SELL ---

    def test_skips_pending_sell_orders(self):
        """Stocks with pending SELL orders should be skipped."""
        depot = _make_depot(
            stocks=[_make_stock(perf="-6.00%")],
            open_orders=[{"isin": "US123", "type": "SELL"}],
        )
        snapshot = {"US123": _make_tech()}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert sells == []

    # --- NO TECH DATA ---

    def test_no_tech_data_hold(self):
        """Stock not in market snapshot -> HOLD (no tech checks possible)."""
        depot = _make_depot(stocks=[_make_stock(perf="+1.00%")])
        sells = algo.analyze_portfolio_safety(depot, [], {})  # empty snapshot
        assert sells == []

    # --- FUZZY TECH MATCH ---

    def test_fuzzy_tech_match_by_name(self):
        """When ISIN not in snapshot, falls back to ticker-in-name match."""
        depot = _make_depot(stocks=[_make_stock(name="TSLA Corp", isin="UNKNOWN", perf="-6.00%")])
        snapshot = {"OTHER_ISIN": _make_tech(ticker="TSLA", price=100)}
        sells = algo.analyze_portfolio_safety(depot, [], snapshot)
        assert len(sells) == 1  # Should find via "TSLA" in "TSLA Corp"


# =========================================================================
# synthesize_decisions
# =========================================================================

class TestSynthesizeDecisions:
    """Tests for synthesize_decisions() - buy decision logic."""

    def _make_ai_entry(self, isin="US999", rating=4.5, sentiment=4.0, earnings="0"):
        return {
            "isin": isin,
            "analyst_rating": rating,
            "news_sentiment": sentiment,
            "earnings_date": earnings,
            "brief_summary": "Strong momentum",
        }

    def test_basic_buy_decision(self):
        depot = _make_depot(cash=50000, stocks=[], open_orders=[])
        tech = {"US999": _make_tech(isin="US999", ticker="NVDA", tech_score=90)}
        ai = [self._make_ai_entry(isin="US999", rating=5.0, sentiment=5.0)]
        # ai_score = ((5+5)/2 - 1) / 4 * 100 = (5-1)/4*100 = 100
        # final_score = 90*0.5 + 100*0.5 = 95 >= 78
        result = algo.synthesize_decisions(depot, tech, ai)
        assert len(result) == 1
        assert result[0]["isin"] == "US999"
        assert result[0]["aktion"] == "BUY"

    def test_insufficient_cash_returns_empty(self):
        depot = _make_depot(cash=100, stocks=[], open_orders=[])
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = [self._make_ai_entry()]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_cash_minus_pending_orders(self):
        """Available cash = displayed - pending buy amounts."""
        depot = _make_depot(
            cash=10000, stocks=[],
            open_orders=[{"isin": "X", "type": "BUY", "betrag_eur": 8000}],
        )
        # Available: 10000 - 8000 = 2000, less than MIN_CASH_FOR_NEW_TRADE=6000
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = [self._make_ai_entry()]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_portfolio_diversity_limit(self):
        """When portfolio is full (5/5), no buys."""
        stocks = [_make_stock(name=f"S{i}", isin=f"IS{i}") for i in range(5)]
        depot = _make_depot(cash=50000, stocks=stocks)
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = [self._make_ai_entry()]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_skips_already_owned(self):
        """Already-owned ISINs should not be bought again."""
        depot = _make_depot(cash=50000, stocks=[_make_stock(isin="US999")])
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = [self._make_ai_entry()]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_skips_pending_buy(self):
        """ISINs with pending BUY orders should not be bought again."""
        depot = _make_depot(
            cash=50000, stocks=[],
            open_orders=[{"isin": "US999", "type": "BUY", "betrag_eur": 5000}],
        )
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = [self._make_ai_entry()]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_score_below_minimum_filtered(self):
        """Candidates below MIN_FINAL_SCORE are rejected."""
        depot = _make_depot(cash=50000, stocks=[])
        tech = {"US999": _make_tech(isin="US999", tech_score=50)}
        ai = [self._make_ai_entry(rating=2.0, sentiment=2.0)]
        # ai_score = ((2+2)/2 - 1) / 4 * 100 = (2-1)/4*100 = 25
        # final_score = 50*0.5 + 25*0.5 = 37.5 < 78
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_earnings_danger_blocks_buy(self):
        """Stock with earnings tomorrow should be blocked."""
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        depot = _make_depot(cash=50000, stocks=[])
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = [self._make_ai_entry(rating=5.0, sentiment=5.0, earnings=tomorrow)]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_no_ai_data_skips_candidate(self):
        """If AI matrix has no entry for an ISIN, it is skipped."""
        depot = _make_depot(cash=50000, stocks=[])
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = []  # empty AI matrix
        result = algo.synthesize_decisions(depot, tech, ai)
        assert result == []

    def test_multiple_candidates_sorted_by_score(self):
        """Higher-scored candidates should be bought first."""
        depot = _make_depot(cash=50000, stocks=[])
        tech = {
            "A": _make_tech(isin="A", ticker="AAA", tech_score=90),
            "B": _make_tech(isin="B", ticker="BBB", tech_score=95),
        }
        ai = [
            self._make_ai_entry(isin="A", rating=5.0, sentiment=5.0),
            self._make_ai_entry(isin="B", rating=5.0, sentiment=5.0),
        ]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert len(result) == 2
        # B has higher tech_score so higher final_score -> first
        assert result[0]["isin"] == "B"

    def test_max_positions_per_cycle_cap(self, monkeypatch):
        """Should not buy more than MAX_NEW_POSITIONS_PER_CYCLE."""
        monkeypatch.setattr(algo.config, "MAX_NEW_POSITIONS_PER_CYCLE", 1)
        depot = _make_depot(cash=50000, stocks=[])
        tech = {
            "A": _make_tech(isin="A", ticker="AAA", tech_score=90),
            "B": _make_tech(isin="B", ticker="BBB", tech_score=95),
        }
        ai = [
            self._make_ai_entry(isin="A", rating=5.0, sentiment=5.0),
            self._make_ai_entry(isin="B", rating=5.0, sentiment=5.0),
        ]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert len(result) == 1

    def test_invest_amount_capped_by_max(self, monkeypatch):
        """Each buy amount should not exceed MAX_INVEST_PER_STOCK."""
        monkeypatch.setattr(algo.config, "MAX_INVEST_PER_STOCK", 8000)
        depot = _make_depot(cash=50000, stocks=[])
        tech = {"US999": _make_tech(isin="US999", tech_score=90)}
        ai = [self._make_ai_entry(rating=5.0, sentiment=5.0)]
        result = algo.synthesize_decisions(depot, tech, ai)
        assert len(result) == 1
        assert result[0]["betrag_eur"] <= 8000


# =========================================================================
# calculate_algo_decisions
# =========================================================================

class TestCalculateAlgoDecisions:
    """Tests for calculate_algo_decisions() - currently a stub."""

    def test_returns_empty_list(self):
        assert algo.calculate_algo_decisions({}) == []

    def test_returns_empty_with_data(self):
        assert algo.calculate_algo_decisions(_make_depot()) == []
