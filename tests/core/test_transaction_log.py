"""
Unit tests for core.transaction_log

Functions tested:
    - log_success
    - get_todays_log_content
    - get_transaction_history
    - print_analysis_summary
"""

import os
from datetime import datetime

import pytest

from core.transaction_log import (
    get_todays_log_content,
    get_transaction_history,
    log_success,
    print_analysis_summary,
)


# =========================================================================
# print_analysis_summary
# =========================================================================

class TestPrintAnalysisSummary:
    """Tests for print_analysis_summary() - stdout output verification."""

    def test_empty_decisions(self, capsys):
        print_analysis_summary([])
        captured = capsys.readouterr().out
        assert "HOLD" in captured or "no actions" in captured.lower()

    def test_none_decisions(self, capsys):
        print_analysis_summary(None)
        captured = capsys.readouterr().out
        assert "no actions" in captured.lower()

    def test_buy_decision(self, capsys):
        decisions = [{"aktion": "BUY", "name": "Apple", "isin": "US123",
                       "betrag_eur": 500, "grund": "Strong momentum"}]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "BUY" in captured
        assert "Apple" in captured
        assert "US123" in captured

    def test_sell_decision(self, capsys):
        decisions = [{"aktion": "SELL", "name": "Tesla", "grund": "Stop loss"}]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "SELL" in captured
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
        assert "2 action" in captured.lower()

    def test_missing_fields_use_defaults(self, capsys):
        """Decisions with missing keys should not crash."""
        decisions = [{}]
        print_analysis_summary(decisions)
        captured = capsys.readouterr().out
        assert "Unknown" in captured


# =========================================================================
# log_success
# =========================================================================

class TestLogSuccess:
    """Tests for log_success() - file-based transaction logging."""

    def test_creates_log_file(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("BUY", "Apple", "US123", 10, 150.0, "Momentum")

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        assert os.path.exists(logfile)

    def test_log_content_format(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
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
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("SELL", "Tesla", "US456", 5, 200.0, "Stop loss", profit=25.5)

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "r") as f:
            content = f.read()
        assert "PROFIT: 25.5" in content

    def test_log_without_profit(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("BUY", "X", "Y", 1, 1.0, "r")

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "r") as f:
            content = f.read()
        assert "PROFIT: N/A" in content

    def test_appends_multiple_entries(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        log_success("BUY", "A", "I1", 1, 1.0, "r1")
        log_success("SELL", "B", "I2", 2, 2.0, "r2")

        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_creates_log_dir_if_missing(self, tmp_path, monkeypatch):
        log_dir = str(tmp_path / "nonexistent" / "logs")
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", log_dir)
        log_success("BUY", "X", "Y", 1, 1.0, "r")
        assert os.path.isdir(log_dir)


# =========================================================================
# get_todays_log_content
# =========================================================================

class TestGetTodaysLogContent:
    """Tests for get_todays_log_content()."""

    def test_returns_content_when_file_exists(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "w") as f:
            f.write("ACTION: BUY | NAME: Test\n")

        result = get_todays_log_content()
        assert "ACTION: BUY" in result

    def test_returns_default_when_no_file(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        result = get_todays_log_content()
        assert "No transactions" in result

    def test_returns_default_when_file_empty(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(tmp_dirs["log_dir"], f"log_{today}.txt")
        with open(logfile, "w") as f:
            f.write("")

        result = get_todays_log_content()
        assert "No transactions" in result


# =========================================================================
# get_transaction_history
# =========================================================================

class TestGetTransactionHistory:
    """Tests for get_transaction_history() - multi-file log parser."""

    def _write_log_file(self, log_dir, date_str, lines):
        filepath = os.path.join(log_dir, f"log_{date_str}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def test_empty_log_dir(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        result = get_transaction_history()
        assert result == []

    def test_nonexistent_log_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", str(tmp_path / "nope"))
        result = get_transaction_history()
        assert result == []

    def test_parses_single_buy_entry(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
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
        assert entry["date"] == "2026-02-11"
        assert entry["action"] == "BUY"
        assert entry["name"] == "Apple Inc."
        assert entry["isin"] == "US0378331005"
        assert entry["profit"] == "-"

    def test_parses_sell_entry_with_profit(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
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
        assert result[0]["profit"] == "+50.00 \u20ac"

    def test_skips_non_action_lines(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        lines = [
            "--- LOG START ---\n",
            "Some debug output\n",
            "[10:00:00] ACTION: BUY  | NAME: X | ISIN: Y | QTY: 1 | PRICE_EST: 1 | PROFIT: N/A | REASON: r\n",
        ]
        self._write_log_file(tmp_dirs["log_dir"], "2026-01-01", lines)

        result = get_transaction_history()
        assert len(result) == 1

    def test_multiple_files_sorted_reverse(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.transaction_log.config.LOG_DIR", tmp_dirs["log_dir"])
        line_template = "[10:00:00] ACTION: BUY  | NAME: {name} | ISIN: X | QTY: 1 | PRICE_EST: 1 | PROFIT: N/A | REASON: r\n"

        self._write_log_file(tmp_dirs["log_dir"], "2026-01-01",
                             [line_template.format(name="Older")])
        self._write_log_file(tmp_dirs["log_dir"], "2026-02-01",
                             [line_template.format(name="Newer")])

        result = get_transaction_history()
        assert len(result) == 2
        assert result[0]["date"] == "2026-02-01"
        assert result[1]["date"] == "2026-01-01"
