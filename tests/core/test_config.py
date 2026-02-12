"""
Unit tests for core.config

Tested:
    - _load_web_config  (reads ai_config.json for web_config flag)
    - Config constants   (type & existence validation)

Note: config.py executes at import time (reads config.yml). The YAML
file must exist for the module to load. These tests validate the
resulting constants and the _load_web_config helper.
"""

import json
import os

import pytest

from core import config


# =========================================================================
# _load_web_config
# =========================================================================

class TestLoadWebConfig:
    """Tests for _load_web_config() - reads web_config flag from JSON."""

    def test_returns_false_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "CONFIG_DIR", str(tmp_path))
        assert config._load_web_config() is False

    def test_returns_true_when_web_config_set(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "ai_config.json"
        cfg_file.write_text(json.dumps({"web_config": True}))
        monkeypatch.setattr(config, "CONFIG_DIR", str(tmp_path))
        assert config._load_web_config() is True

    def test_returns_false_when_web_config_missing(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "ai_config.json"
        cfg_file.write_text(json.dumps({"provider": "openai"}))
        monkeypatch.setattr(config, "CONFIG_DIR", str(tmp_path))
        assert config._load_web_config() is False

    def test_returns_false_on_corrupt_json(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "ai_config.json"
        cfg_file.write_text("{{{bad json")
        monkeypatch.setattr(config, "CONFIG_DIR", str(tmp_path))
        assert config._load_web_config() is False

    def test_returns_false_when_web_config_is_false(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "ai_config.json"
        cfg_file.write_text(json.dumps({"web_config": False}))
        monkeypatch.setattr(config, "CONFIG_DIR", str(tmp_path))
        assert config._load_web_config() is False


# =========================================================================
# Config constants - type & value validation
# =========================================================================

class TestConfigConstants:
    """Verify key config constants are loaded with correct types."""

    def test_urls_are_strings(self):
        assert isinstance(config.OON_LOGIN_URL, str)
        assert len(config.OON_LOGIN_URL) > 0
        assert isinstance(config.OON_DEPOT_URL, str)
        assert len(config.OON_DEPOT_URL) > 0

    def test_timing_values_are_positive(self):
        assert config.CHECK_INTERVAL_SECONDS > 0
        assert config.AI_CYCLE_INTERVAL_SECONDS > 0
        assert config.ERROR_WAIT_SECONDS > 0

    def test_ai_cycle_longer_than_check(self):
        assert config.AI_CYCLE_INTERVAL_SECONDS > config.CHECK_INTERVAL_SECONDS

    def test_risk_management_values(self):
        assert config.MIN_TRADE_VOLUME > 0
        assert config.MAX_INVEST_PER_STOCK > config.MIN_TRADE_VOLUME
        assert config.PORTFOLIO_DIVERSITY > 0
        assert config.MIN_CASH_FOR_NEW_TRADE > 0

    def test_profit_loss_thresholds(self):
        assert config.STOP_LOSS_HARD_PCT < 0
        assert config.TAKE_PROFIT_HARD_PCT > 0

    def test_hwm_values(self):
        assert config.HWM_TRIGGER_PCT > 0
        assert config.HWM_DROP_THRESHOLD > 0

    def test_technical_indicator_params(self):
        assert config.RSI_PERIOD > 0
        assert config.RSI_OVERBOUGHT > config.RSI_OVERSOLD
        assert config.EMA_FAST > 0
        assert config.EMA_SLOW > config.EMA_FAST

    def test_strategy_weights_sum_to_one(self):
        total = config.AI_WEIGHT + config.TECH_WEIGHT
        assert abs(total - 1.0) < 0.01

    def test_directories_are_strings(self):
        assert isinstance(config.LOG_DIR, str)
        assert isinstance(config.JSON_DIR, str)
        assert isinstance(config.CONFIG_DIR, str)
        assert isinstance(config.USER_DATA_DIR, str)

    def test_fee_values_exist(self):
        assert config.TRANSACTION_FEE_BUY >= 0
        assert config.TRANSACTION_FEE_SELL >= 0

    def test_market_timing_values(self):
        assert 0 <= config.MARKET_CLOSE_HOUR_EU <= 23
        assert 0 <= config.MARKET_CLOSE_MINUTE_EU <= 59
        assert 0 <= config.MARKET_CLOSE_HOUR_US <= 23
        assert 0 <= config.MARKET_CLOSE_MINUTE_US <= 59

    def test_browser_show_is_bool(self):
        assert isinstance(config.BROWSER_SHOW, bool)

    def test_test_mode_is_bool(self):
        assert isinstance(config.TEST_MODE, bool)
