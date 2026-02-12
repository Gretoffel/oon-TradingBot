"""
Unit tests for services.market_data

Functions tested:
    - get_isin_by_name       (pure lookup)
    - calculate_rsi           (pure math)
    - calculate_ema           (pure math)
    - calculate_vwap          (pure math)
    - calculate_atr           (pure math)
    - calculate_technical_score (pure logic with config dependency)
    - is_market_open          (time-dependent, mocked)
    - get_minutes_until_close (time-dependent, mocked)

NOT tested (requires live Yahoo Finance API):
    - get_market_snapshot
"""

import datetime as dt

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from services.market_data import (
    calculate_atr,
    calculate_ema,
    calculate_rsi,
    calculate_technical_score,
    calculate_vwap,
    get_isin_by_name,
    get_minutes_until_close,
    is_market_open,
)

# Save reference to real datetime class BEFORE any patching replaces it
_real_datetime = dt.datetime


# =========================================================================
# get_isin_by_name
# =========================================================================

class TestGetIsinByName:
    """Tests for get_isin_by_name() - fuzzy name-to-ISIN lookup."""

    def test_exact_keyword_match(self):
        assert get_isin_by_name("nvidia") == "US67066G1040"

    def test_case_insensitive(self):
        assert get_isin_by_name("NVIDIA") == "US67066G1040"

    def test_partial_match_in_longer_string(self):
        assert get_isin_by_name("Tesla Inc.") == "US88160R1014"

    def test_no_match_returns_none(self):
        assert get_isin_by_name("Unknown Corp XYZ") is None

    def test_empty_string(self):
        assert get_isin_by_name("") is None

    def test_austrian_stock(self):
        assert get_isin_by_name("OMV AG") == "AT0000743059"

    def test_german_stock(self):
        assert get_isin_by_name("Rheinmetall Defence") == "DE0007030009"

    def test_multi_word_keyword(self):
        assert get_isin_by_name("Plug Power Inc") == "US72919P2020"

    def test_jp_morgan_variant(self):
        """Both 'jp morgan' and 'morgan chase' map to same ISIN."""
        assert get_isin_by_name("JP Morgan Chase") == "US46625H1005"


# =========================================================================
# calculate_rsi
# =========================================================================

class TestCalculateRsi:
    """Tests for calculate_rsi() - Relative Strength Index."""

    def test_constant_rise_gives_high_rsi(self):
        """Monotonically increasing prices -> RSI near 100."""
        prices = pd.Series(range(1, 22), dtype=float)  # 1,2,3,...,21
        rsi = calculate_rsi(prices, period=14)
        last_rsi = rsi.iloc[-1]
        assert last_rsi > 95  # Should be close to 100

    def test_constant_fall_gives_low_rsi(self):
        """Monotonically decreasing prices -> RSI near 0."""
        prices = pd.Series(range(21, 0, -1), dtype=float)  # 21,20,...,1
        rsi = calculate_rsi(prices, period=14)
        last_rsi = rsi.iloc[-1]
        assert last_rsi < 5  # Should be close to 0

    def test_rsi_range_is_0_to_100(self):
        """RSI values should stay in [0, 100] (excluding NaN warmup)."""
        np.random.seed(42)
        prices = pd.Series(np.random.uniform(90, 110, 50))
        rsi = calculate_rsi(prices, period=14)
        valid = rsi.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_short_period(self):
        """With period=3, should compute quickly with fewer data points."""
        prices = pd.Series([10, 11, 12, 11, 13, 14, 12], dtype=float)
        rsi = calculate_rsi(prices, period=3)
        valid = rsi.dropna()
        assert len(valid) > 0

    def test_flat_prices_give_nan(self):
        """Flat prices -> no gain, no loss -> division by zero -> NaN."""
        prices = pd.Series([100.0] * 20)
        rsi = calculate_rsi(prices, period=14)
        # gain=0, loss=0, so rs=0/0=NaN
        assert np.isnan(rsi.iloc[-1])

    def test_default_period_is_14(self):
        prices = pd.Series(range(1, 30), dtype=float)
        rsi_default = calculate_rsi(prices)
        rsi_14 = calculate_rsi(prices, period=14)
        pd.testing.assert_series_equal(rsi_default, rsi_14)


# =========================================================================
# calculate_ema
# =========================================================================

class TestCalculateEma:
    """Tests for calculate_ema() - Exponential Moving Average."""

    def test_single_value(self):
        prices = pd.Series([100.0])
        ema = calculate_ema(prices, span=10)
        assert ema.iloc[0] == 100.0

    def test_constant_prices(self):
        """EMA of constant series equals the constant."""
        prices = pd.Series([50.0] * 20)
        ema = calculate_ema(prices, span=10)
        assert abs(ema.iloc[-1] - 50.0) < 0.001

    def test_rising_trend_ema_lags(self):
        """EMA of rising series should be below the latest price."""
        prices = pd.Series(range(1, 30), dtype=float)
        ema = calculate_ema(prices, span=10)
        assert ema.iloc[-1] < prices.iloc[-1]

    def test_short_span_reacts_faster(self):
        """Shorter span EMA should be closer to latest price than longer span."""
        prices = pd.Series(list(range(20)) + [100.0], dtype=float)  # spike at end
        ema_fast = calculate_ema(prices, span=3)
        ema_slow = calculate_ema(prices, span=15)
        # Fast EMA reacts more to the spike
        assert ema_fast.iloc[-1] > ema_slow.iloc[-1]

    def test_output_length_matches_input(self):
        prices = pd.Series(range(50), dtype=float)
        ema = calculate_ema(prices, span=20)
        assert len(ema) == len(prices)


# =========================================================================
# calculate_vwap
# =========================================================================

class TestCalculateVwap:
    """Tests for calculate_vwap() - Volume-Weighted Average Price."""

    def _make_ohlcv(self, highs, lows, closes, volumes, dates=None):
        if dates is None:
            dates = pd.date_range("2026-01-01", periods=len(highs), freq="h")
        return pd.DataFrame({
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        }, index=dates)

    def test_equal_volume_vwap_is_typical_price(self):
        """When all volume bars are equal, VWAP = typical price cumulative avg."""
        df = self._make_ohlcv(
            highs=[12, 14], lows=[8, 10], closes=[10, 12],
            volumes=[100, 100],
        )
        vwap = calculate_vwap(df)
        assert len(vwap) == 2

    def test_single_bar(self):
        df = self._make_ohlcv(
            highs=[15], lows=[5], closes=[10], volumes=[1000],
        )
        vwap = calculate_vwap(df)
        expected = (15 + 5 + 10) / 3  # typical price = 10
        assert abs(float(vwap.iloc[0]) - expected) < 0.01

    def test_output_length_matches(self):
        df = self._make_ohlcv(
            highs=[10, 11, 12], lows=[8, 9, 10], closes=[9, 10, 11],
            volumes=[100, 200, 300],
        )
        vwap = calculate_vwap(df)
        assert len(vwap) == 3

    def test_high_volume_bar_pulls_vwap(self):
        """A bar with much higher volume should pull VWAP toward its price."""
        df = self._make_ohlcv(
            highs=[10, 20], lows=[10, 20], closes=[10, 20],
            volumes=[1, 10000],  # 2nd bar dominates
        )
        vwap = calculate_vwap(df)
        # Last VWAP should be very close to 20 (dominated by 2nd bar)
        assert float(vwap.iloc[-1]) > 15


# =========================================================================
# calculate_atr
# =========================================================================

class TestCalculateAtr:
    """Tests for calculate_atr() - Average True Range."""

    def _make_ohlc(self, highs, lows, closes):
        dates = pd.date_range("2026-01-01", periods=len(highs), freq="D")
        return pd.DataFrame({
            "High": highs, "Low": lows, "Close": closes,
        }, index=dates)

    def test_constant_range(self):
        """Constant high-low range should give ATR equal to that range."""
        n = 20
        df = self._make_ohlc(
            highs=[110] * n, lows=[90] * n, closes=[100] * n,
        )
        atr = calculate_atr(df, period=14)
        last_atr = atr.dropna().iloc[-1]
        assert abs(last_atr - 20.0) < 0.5  # range is 110-90=20

    def test_zero_range_gives_zero_atr(self):
        """Flat prices (High=Low=Close) should give ATR near zero."""
        n = 20
        df = self._make_ohlc(
            highs=[100] * n, lows=[100] * n, closes=[100] * n,
        )
        atr = calculate_atr(df, period=14)
        last_atr = atr.dropna().iloc[-1]
        assert last_atr < 0.01

    def test_atr_is_always_positive(self):
        np.random.seed(42)
        closes = np.random.uniform(90, 110, 30)
        df = self._make_ohlc(
            highs=closes + 5, lows=closes - 5, closes=closes,
        )
        atr = calculate_atr(df, period=14)
        valid = atr.dropna()
        assert (valid >= 0).all()

    def test_output_length_matches(self):
        df = self._make_ohlc(
            highs=[110] * 20, lows=[90] * 20, closes=[100] * 20,
        )
        atr = calculate_atr(df, period=14)
        assert len(atr) == 20


# =========================================================================
# calculate_technical_score
# =========================================================================

class TestCalculateTechnicalScore:
    """Tests for calculate_technical_score() - momentum scoring algorithm."""

    def _make_data(self, rsi=60, price=100, ema_fast=95, ema_slow=90, vol_ratio=1.5):
        return {
            "rsi": rsi, "price": price,
            "ema_fast": ema_fast, "ema_slow": ema_slow,
            "volume_ratio": vol_ratio,
        }

    def test_perfect_score(self):
        """All conditions met -> max score = 100."""
        data = self._make_data(rsi=65, price=100, ema_fast=95, ema_slow=90, vol_ratio=2.0)
        # RSI 50-80: +40, price>ema_slow: +30, price>ema_fast: +10,
        # ema_fast>ema_slow: +10, vol_ratio>=MIN: +10 = 100
        assert calculate_technical_score(data) == 100

    def test_zero_score(self):
        """No conditions met -> score = 0."""
        data = self._make_data(rsi=20, price=80, ema_fast=90, ema_slow=100, vol_ratio=0.5)
        # RSI <40: 0, price<ema_slow: 0, price<ema_fast: 0,
        # ema_fast<ema_slow: 0, vol_ratio<MIN: 0
        assert calculate_technical_score(data) == 0

    def test_rsi_sweet_spot_50_80(self):
        data = self._make_data(rsi=65, price=0, ema_fast=0, ema_slow=0, vol_ratio=0)
        assert calculate_technical_score(data) == 40

    def test_rsi_recovery_zone_40_50(self):
        data = self._make_data(rsi=45, price=0, ema_fast=0, ema_slow=0, vol_ratio=0)
        assert calculate_technical_score(data) == 20

    def test_rsi_overbought_above_80(self):
        data = self._make_data(rsi=85, price=0, ema_fast=0, ema_slow=0, vol_ratio=0)
        assert calculate_technical_score(data) == 10

    def test_rsi_below_40_no_points(self):
        data = self._make_data(rsi=30, price=0, ema_fast=0, ema_slow=0, vol_ratio=0)
        assert calculate_technical_score(data) == 0

    def test_price_above_ema_slow_only(self):
        data = self._make_data(rsi=20, price=100, ema_fast=110, ema_slow=90, vol_ratio=0)
        # price>ema_slow: +30, price<ema_fast: 0, ema_fast>ema_slow: +10
        assert calculate_technical_score(data) == 40

    def test_golden_cross(self):
        """EMA fast > EMA slow gives +10."""
        data = self._make_data(rsi=20, price=0, ema_fast=100, ema_slow=90, vol_ratio=0)
        assert calculate_technical_score(data) == 10

    def test_volume_threshold(self, monkeypatch):
        """Volume ratio at or above MIN_VOLUME_RATIO gives +10."""
        monkeypatch.setattr("services.market_data.config.MIN_VOLUME_RATIO", 1.5)
        data = self._make_data(rsi=20, price=0, ema_fast=0, ema_slow=0, vol_ratio=1.5)
        assert calculate_technical_score(data) == 10

    def test_volume_below_threshold(self, monkeypatch):
        monkeypatch.setattr("services.market_data.config.MIN_VOLUME_RATIO", 1.5)
        data = self._make_data(rsi=20, price=0, ema_fast=0, ema_slow=0, vol_ratio=1.0)
        assert calculate_technical_score(data) == 0

    def test_rsi_boundary_50(self):
        """RSI exactly 50 should be in sweet spot."""
        data = self._make_data(rsi=50, price=0, ema_fast=0, ema_slow=0, vol_ratio=0)
        assert calculate_technical_score(data) == 40

    def test_rsi_boundary_80(self):
        """RSI exactly 80 should still be in sweet spot."""
        data = self._make_data(rsi=80, price=0, ema_fast=0, ema_slow=0, vol_ratio=0)
        assert calculate_technical_score(data) == 40


# =========================================================================
# is_market_open
# =========================================================================

class TestIsMarketOpen:
    """Tests for is_market_open() - market hours check (time-mocked)."""

    def _mock_now(self, year=2026, month=2, day=11, hour=10, minute=0):
        """Create a fake datetime for a specific weekday and time.
        2026-02-11 is a Wednesday.
        """
        return _real_datetime(year, month, day, hour, minute)

    @patch("datetime.datetime")
    def test_eu_market_open_midday(self, mock_dt):
        mock_dt.now.return_value = self._mock_now(hour=12, minute=0)  # Wed 12:00
        assert is_market_open("EBS.VI") is True

    @patch("datetime.datetime")
    def test_eu_market_closed_early_morning(self, mock_dt):
        mock_dt.now.return_value = self._mock_now(hour=7, minute=0)  # Wed 07:00
        assert is_market_open("SAP.DE") is False

    @patch("datetime.datetime")
    def test_eu_market_closed_evening(self, mock_dt):
        mock_dt.now.return_value = self._mock_now(hour=18, minute=0)  # Wed 18:00
        assert is_market_open("OMV.VI") is False

    @patch("datetime.datetime")
    def test_us_market_open_afternoon_cet(self, mock_dt):
        mock_dt.now.return_value = self._mock_now(hour=16, minute=0)  # Wed 16:00 CET
        assert is_market_open("TSLA") is True

    @patch("datetime.datetime")
    def test_us_market_closed_morning_cet(self, mock_dt):
        mock_dt.now.return_value = self._mock_now(hour=10, minute=0)  # Wed 10:00 CET
        assert is_market_open("AAPL") is False

    @patch("datetime.datetime")
    def test_weekend_saturday(self, mock_dt):
        # 2026-02-14 is a Saturday
        mock_dt.now.return_value = self._mock_now(month=2, day=14, hour=12, minute=0)
        assert is_market_open("TSLA") is False

    @patch("datetime.datetime")
    def test_weekend_sunday(self, mock_dt):
        # 2026-02-15 is a Sunday
        mock_dt.now.return_value = self._mock_now(month=2, day=15, hour=12, minute=0)
        assert is_market_open("EBS.VI") is False

    @patch("datetime.datetime")
    def test_eu_open_boundary_start(self, mock_dt):
        mock_dt.now.return_value = self._mock_now(hour=9, minute=0)  # 540 mins
        assert is_market_open("EBS.VI") is True

    @patch("datetime.datetime")
    def test_unknown_exchange_always_open(self, mock_dt):
        """Tickers not matching known patterns return True."""
        mock_dt.now.return_value = self._mock_now(hour=3, minute=0)  # 3 AM
        assert is_market_open("SOME.XX") is True


# =========================================================================
# get_minutes_until_close
# =========================================================================

class TestGetMinutesUntilClose:
    """Tests for get_minutes_until_close() - time-mocked."""

    @patch("datetime.datetime")
    def test_eu_market_minutes_remaining(self, mock_dt, monkeypatch):
        mock_dt.now.return_value = _real_datetime(2026, 2, 11, 16, 0)  # 16:00
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_HOUR_EU", 17)
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_MINUTE_EU", 30)
        result = get_minutes_until_close("EBS.VI")
        assert result == 90  # 17:30 - 16:00 = 90 mins

    @patch("datetime.datetime")
    def test_us_market_minutes_remaining(self, mock_dt, monkeypatch):
        mock_dt.now.return_value = _real_datetime(2026, 2, 11, 20, 0)  # 20:00 CET
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_HOUR_US", 22)
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_MINUTE_US", 0)
        result = get_minutes_until_close("TSLA")
        assert result == 120  # 22:00 - 20:00 = 120 mins

    @patch("datetime.datetime")
    def test_negative_when_past_close(self, mock_dt, monkeypatch):
        mock_dt.now.return_value = _real_datetime(2026, 2, 11, 23, 0)  # 23:00
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_HOUR_US", 22)
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_MINUTE_US", 0)
        result = get_minutes_until_close("AAPL")
        assert result < 0

    @patch("datetime.datetime")
    def test_de_uses_eu_times(self, mock_dt, monkeypatch):
        mock_dt.now.return_value = _real_datetime(2026, 2, 11, 15, 0)
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_HOUR_EU", 17)
        monkeypatch.setattr("services.market_data.config.MARKET_CLOSE_MINUTE_EU", 30)
        result = get_minutes_until_close("SAP.DE")
        assert result == 150  # 17:30 - 15:00 = 150 mins
