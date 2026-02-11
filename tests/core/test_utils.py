"""
Unit tests for core.utils

Functions tested:
    - clean_amount
    - calculate_fee
    - extract_json_list
    - print_analysis_summary
    - log_success
    - get_todays_log_content
    - get_transaction_history
    - load_blacklist
    - save_blacklist
    - add_to_blacklist

Complexity notes:
    - get_transaction_history: High cyclomatic complexity (nested loops, nested
      try/except, bare excepts that silently swallow errors). Still testable but
      the function would benefit from being split into smaller helpers.
"""

import json
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from core.utils import (
    add_to_blacklist,
    calculate_fee,
    clean_amount,
    extract_json_list,
    get_todays_log_content,
    get_transaction_history,
    load_blacklist,
    log_success,
    print_analysis_summary,
    save_blacklist,
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
        assert clean_amount("1.200,50 €") == 1200.50

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
        # 0.25% of 1000 = 2.50, which is < 17, so base = 17
        assert calculate_fee(1000) == 17.0 + 3.0

    def test_percentage_fee_applies(self):
        """Large amounts should use the 0.25% rate."""
        # 0.25% of 10000 = 25.00, which is > 17, so base = 25
        assert calculate_fee(10000) == 25.0 + 3.0

    def test_breakeven_point(self):
        """At 6800 EUR, 0.25% = 17, which equals the minimum."""
        assert calculate_fee(6800) == 17.0 + 3.0

    def test_just_above_breakeven(self):
        """Just above the breakeven: percentage fee > minimum."""
        result = calculate_fee(7000)
        expected = 7000 * 0.0025 + 3.0  # 17.5 + 3 = 20.5
        assert result == expected

    def test_fee_always_includes_flat(self):
        """Every non-zero trade has the 3 EUR flat surcharge."""
        assert calculate_fee(100) >= 3.0

    def test_very_small_amount(self):
        """Even 1 EUR trade gets minimum fee."""
        assert calculate_fee(1) == 20.0  # 17 + 3


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


# =========================================================================
# print_analysis_summary
# =========================================================================

class TestPrintAnalysisSummary:
    """Tests for print_analysis_summary() - stdout output verification."""

    def test_empty_decisions(self, capsys):
        print_analysis_summary([])
        captured = capsys.readouterr().out
        assert "HOLD" in captured or "keine Aktionen" in captured

    def test_none_decisions(self, capsys):
        print_analysis_summary(None)
        captured = capsys.readouterr().out
        assert "keine Aktionen" in captured

    def test_buy_decision(self, capsys):
        decisions = [{"aktion": "BUY", "name": "Apple", "isin": "US123",
                       "betrag_eur": 500, "grund": "Strong momentum"}]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "KAUFEN" in captured
        assert "Apple" in captured
        assert "US123" in captured

    def test_sell_decision(self, capsys):
        decisions = [{"aktion": "SELL", "name": "Tesla", "grund": "Stop loss"}]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "VERKAUFEN" in captured
        assert "Tesla" in captured

    def test_unknown_action(self, capsys):
        decisions = [{"aktion": "HOLD", "name": "MSFT", "grund": "Wait"}]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "HOLD" in captured
        assert "MSFT" in captured

    def test_multiple_decisions(self, capsys):
        decisions = [
            {"aktion": "BUY", "name": "A", "isin": "X", "betrag_eur": 1, "grund": "r1"},
            {"aktion": "SELL", "name": "B", "grund": "r2"},
        ]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "2 Aktionen" in captured

    def test_missing_fields_use_defaults(self, capsys):
        """Decisions with missing keys should not crash."""
        decisions = [{}]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "Unbekannt" in captured


# =========================================================================
# log_success
# =========================================================================

class TestLogSuccess:
    """Tests for log_success() - file-based transaction logging."""

    def test_creates_log_file(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("BUY", "Apple", "US123", 10, 150.0, "Momentum")

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        assert os.path.exists(logfile)

    def test_log_content_format(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("BUY", "Apple", "US123", 10, 150.0, "Momentum")

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "r") as f:
            content = f.read()
        assert "ACTION: BUY" in content
        assert "NAME: Apple" in content
        assert "ISIN: US123" in content
        assert "QTY: 10" in content
        assert "REASON: Momentum" in content

    def test_log_with_profit(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("SELL", "Tesla", "US456", 5, 200.0, "Stop loss", profit=25.5)

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "r") as f:
            content = f.read()
        assert "PROFIT: 25.5" in content

    def test_log_without_profit(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("BUY", "X", "Y", 1, 1.0, "r")

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "r") as f:
            content = f.read()
        assert "PROFIT: N/A" in content

    def test_appends_multiple_entries(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("BUY", "A", "I1", 1, 1.0, "r1")
        log_success("SELL", "B", "I2", 2, 2.0, "r2")

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_creates_log_dir_if_missing(self, tmp_path, monkeypatch):
        log_dir = str(tmp_path / "nonexistent" / "logs")
        monkeypatch.setattr("core.utils.config.LOG_DIR", log_dir)
        log_success("BUY", "X", "Y", 1, 1.0, "r")
        assert os.path.isdir(log_dir)


# =========================================================================
# get_todays_log_content
# =========================================================================

class TestGetTodaysLogContent:
    """Tests for get_todays_log_content()."""

    def test_returns_content_when_file_exists(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "w") as f:
            f.write("ACTION: BUY | NAME: Test\n")

        result = get_todays_log_content()
        assert "ACTION: BUY" in result

    def test_returns_default_when_no_file(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        result = get_todays_log_content()
        assert "Keine Transaktionen" in result

    def test_returns_default_when_file_empty(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "w") as f:
            f.write("")

        result = get_todays_log_content()
        assert "Keine Transaktionen" in result


# =========================================================================
# get_transaction_history
# =========================================================================

class TestGetTransactionHistory:
    """Tests for get_transaction_history() - multi-file log parser.

    NOTE: This function has high cyclomatic complexity. It combines file
    discovery, line-by-line parsing, and field extraction in a single function
    with nested try/except blocks and bare excepts. It works, but would
    benefit from being decomposed into: find_log_files(), parse_log_line(),
    and a top-level orchestrator.
    """

    def _write_log_file(self, log_dir, date_str, lines):
        filepath = os.path.join(log_dir, f"log_{date_str}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def test_empty_log_dir(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        result = get_transaction_history()
        assert result == []

    def test_nonexistent_log_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", str(tmp_path / "nope"))
        result = get_transaction_history()
        assert result == []

    def test_parses_single_buy_entry(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        line = (
            "[10:30:00] ACTION: BUY  | "
            "NAME: Apple Inc.          | "
            "ISIN: US0378331005 | "
            "QTY: 10    | "
            "PRICE_EST: 150.00   | "
            "PROFIT: N/A | "
            "REASON: Momentum\n"
        )
        self._write_log_file(tmp_dirs["log_dir"], "2026-02-11", [line])

        result = get_transaction_history()
        assert len(result) == 1
        entry = result[0]
        assert entry["Datum"] == "2026-02-11"
        assert entry["Aktion"] == "BUY"
        assert entry["Name"] == "Apple Inc."
        assert entry["ISIN"] == "US0378331005"
        assert entry["Profit"] == "-"

    def test_parses_sell_entry_with_profit(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        line = (
            "[14:00:00] ACTION: SELL | "
            "NAME: Tesla               | "
            "ISIN: US88160R1014 | "
            "QTY: 5     | "
            "PRICE_EST: 200.00   | "
            "PROFIT: 50.0 | "
            "REASON: Take profit\n"
        )
        self._write_log_file(tmp_dirs["log_dir"], "2026-02-10", [line])

        result = get_transaction_history()
        assert len(result) == 1
        assert result[0]["Profit"] == "+50.00 \u20ac"

    def test_skips_non_action_lines(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        lines = [
            "--- LOG START ---\n",
            "Some debug output\n",
            "[10:00:00] ACTION: BUY  | NAME: X | ISIN: Y | QTY: 1 | PRICE_EST: 1 | PROFIT: N/A | REASON: r\n",
        ]
        self._write_log_file(tmp_dirs["log_dir"], "2026-01-01", lines)

        result = get_transaction_history()
        assert len(result) == 1

    def test_multiple_files_sorted_reverse(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.LOG_DIR", tmp_dirs["log_dir"])
        line_template = "[10:00:00] ACTION: BUY  | NAME: {name} | ISIN: X | QTY: 1 | PRICE_EST: 1 | PROFIT: N/A | REASON: r\n"

        self._write_log_file(tmp_dirs["log_dir"], "2026-01-01",
                             [line_template.format(name="Older")])
        self._write_log_file(tmp_dirs["log_dir"], "2026-02-01",
                             [line_template.format(name="Newer")])

        result = get_transaction_history()
        assert len(result) == 2
        # Newer date file processed first (reverse sort)
        assert result[0]["Datum"] == "2026-02-01"
        assert result[1]["Datum"] == "2026-01-01"


# =========================================================================
# load_blacklist / save_blacklist / add_to_blacklist
# =========================================================================

class TestBlacklist:
    """Tests for the blacklist management functions."""

    def test_load_empty_when_file_missing(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        assert load_blacklist() == []

    def test_save_and_load_roundtrip(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.utils.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        data = [{"id": "US123", "reason": "Not tradeable", "date": "2026-01-01"}]
        save_blacklist(data)
        loaded = load_blacklist()
        assert loaded == data

    def test_load_returns_empty_for_dict_format(self, tmp_dirs, monkeypatch):
        """Old format was a dict - should gracefully return empty list."""
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        with open(tmp_dirs["blacklist_file"], "w") as f:
            json.dump({"old": "format"}, f)
        assert load_blacklist() == []

    def test_load_returns_empty_for_corrupted_file(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        with open(tmp_dirs["blacklist_file"], "w") as f:
            f.write("{{{corrupt json")
        assert load_blacklist() == []

    def test_add_to_blacklist_creates_entry(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.utils.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist("US999", "Test reason")
        loaded = load_blacklist()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "US999"
        assert loaded[0]["reason"] == "Test reason"
        assert "date" in loaded[0]

    def test_add_to_blacklist_no_duplicates(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.utils.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist("US999", "First")
        add_to_blacklist("US999", "Second")
        loaded = load_blacklist()
        assert len(loaded) == 1

    def test_add_to_blacklist_ignores_none(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.utils.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist(None)
        add_to_blacklist("")
        add_to_blacklist("N/A")
        assert not os.path.exists(tmp_dirs["blacklist_file"])

    def test_add_multiple_different_entries(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.utils.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist("US111", "Reason A")
        add_to_blacklist("US222", "Reason B")
        loaded = load_blacklist()
        assert len(loaded) == 2

    def test_save_creates_json_dir_if_missing(self, tmp_path, monkeypatch):
        new_dir = str(tmp_path / "new_json")
        bl_file = os.path.join(new_dir, "blacklist.json")
        monkeypatch.setattr("core.utils.config.BLACKLIST_FILE", bl_file)
        monkeypatch.setattr("core.utils.config.JSON_DIR", new_dir)
        save_blacklist([{"id": "X", "reason": "test", "date": "now"}])
        assert os.path.isdir(new_dir)
        assert os.path.exists(bl_file)
