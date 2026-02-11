"""
Unit tests for core.remote_manager

Functions tested:
    - _ensure_json_dir
    - update_status
    - get_state
    - get_command
    - set_command
    - get_high_water_marks
    - save_high_water_marks
    - get_live_logs

Complexity notes:
    - update_status: Has 6 parameters and merges with previously persisted state
      (read-modify-write pattern). Each optional param triggers a conditional
      fallback to existing data. Still testable but the branching is dense.
      Consider splitting into update_status() + _merge_state().
"""

import json
import os

import pytest

import core.remote_manager as rm


@pytest.fixture(autouse=True)
def isolate_remote_manager(tmp_dirs, monkeypatch):
    """Redirect all file paths in remote_manager to temp directories."""
    monkeypatch.setattr(rm, "JSON_DIR", tmp_dirs["json_dir"])
    monkeypatch.setattr(rm, "STATE_FILE", tmp_dirs["state_file"])
    monkeypatch.setattr(rm, "CONTROL_FILE", tmp_dirs["control_file"])
    monkeypatch.setattr(rm, "SESSION_LOG_FILE", tmp_dirs["session_log"])


# =========================================================================
# _ensure_json_dir
# =========================================================================

class TestEnsureJsonDir:
    """Tests for _ensure_json_dir() - directory creation guard."""

    def test_creates_dir_when_missing(self, tmp_path, monkeypatch):
        new_dir = str(tmp_path / "brand_new")
        monkeypatch.setattr(rm, "JSON_DIR", new_dir)
        rm._ensure_json_dir()
        assert os.path.isdir(new_dir)

    def test_noop_when_dir_exists(self, tmp_dirs):
        """Should not raise when directory already exists."""
        rm._ensure_json_dir()
        rm._ensure_json_dir()  # idempotent
        assert os.path.isdir(tmp_dirs["json_dir"])


# =========================================================================
# get_command / set_command
# =========================================================================

class TestCommand:
    """Tests for get_command() and set_command()."""

    def test_default_command_is_run(self, tmp_dirs):
        """When no control file exists, default is 'run'."""
        assert rm.get_command() == "run"

    def test_set_and_get_command(self, tmp_dirs):
        rm.set_command("stop")
        assert rm.get_command() == "stop"

    def test_set_command_overwrites(self, tmp_dirs):
        rm.set_command("stop")
        rm.set_command("run")
        assert rm.get_command() == "run"

    def test_get_command_returns_run_on_corrupt_file(self, tmp_dirs):
        with open(tmp_dirs["control_file"], "w") as f:
            f.write("{{{bad json")
        assert rm.get_command() == "run"

    def test_set_command_creates_file(self, tmp_dirs):
        rm.set_command("test_cmd")
        assert os.path.exists(tmp_dirs["control_file"])
        with open(tmp_dirs["control_file"], "r") as f:
            data = json.load(f)
        assert data["command"] == "test_cmd"


# =========================================================================
# get_state
# =========================================================================

class TestGetState:
    """Tests for get_state()."""

    def test_default_state_when_no_file(self, tmp_dirs):
        state = rm.get_state()
        assert state["phase"] == "Offline"
        assert state["balance"] == 0
        assert state["portfolio"] == []
        assert state["high_water_marks"] == {}

    def test_returns_fehler_on_corrupt_file(self, tmp_dirs):
        with open(tmp_dirs["state_file"], "w") as f:
            f.write("not valid json!!!")
        state = rm.get_state()
        assert state["phase"] == "Fehler"

    def test_reads_existing_state(self, tmp_dirs):
        data = {
            "phase": "Active",
            "details": "Running",
            "balance": 5000.0,
            "portfolio": [{"name": "AAPL"}],
            "high_water_marks": {"US123": 5.0},
        }
        with open(tmp_dirs["state_file"], "w") as f:
            json.dump(data, f)
        state = rm.get_state()
        assert state["phase"] == "Active"
        assert state["balance"] == 5000.0
        assert state["portfolio"] == [{"name": "AAPL"}]


# =========================================================================
# update_status
# =========================================================================

class TestUpdateStatus:
    """Tests for update_status() - state persistence with merge logic.

    NOTE: This function has 6 parameters and implements a read-modify-write
    pattern with conditional fallbacks. Each None-valued optional parameter
    triggers a fallback to previously persisted data. While testable, this
    merge logic adds hidden coupling between consecutive calls.
    """

    def test_basic_write(self, tmp_dirs):
        rm.update_status("Active", "Running", balance=1000.0)
        state = rm.get_state()
        assert state["phase"] == "Active"
        assert state["details"] == "Running"
        assert state["balance"] == 1000.0
        assert state["is_alive"] is True

    def test_preserves_portfolio_when_not_passed(self, tmp_dirs):
        """Passing portfolio=None should keep previous portfolio data."""
        rm.update_status("A", portfolio=[{"name": "AAPL"}])
        rm.update_status("B")  # portfolio=None -> keep previous
        state = rm.get_state()
        assert state["portfolio"] == [{"name": "AAPL"}]

    def test_overwrites_portfolio_when_passed(self, tmp_dirs):
        rm.update_status("A", portfolio=[{"name": "AAPL"}])
        rm.update_status("B", portfolio=[{"name": "TSLA"}])
        state = rm.get_state()
        assert state["portfolio"] == [{"name": "TSLA"}]

    def test_preserves_hwm_when_not_passed(self, tmp_dirs):
        rm.update_status("A", high_water_marks={"US123": 5.0})
        rm.update_status("B")
        state = rm.get_state()
        assert state["high_water_marks"] == {"US123": 5.0}

    def test_overwrites_hwm_when_passed(self, tmp_dirs):
        rm.update_status("A", high_water_marks={"US123": 5.0})
        rm.update_status("B", high_water_marks={"US999": 10.0})
        state = rm.get_state()
        assert state["high_water_marks"] == {"US999": 10.0}

    def test_preserves_open_orders_when_not_passed(self, tmp_dirs):
        rm.update_status("A", open_orders=[{"type": "BUY"}])
        rm.update_status("B")
        state = rm.get_state()
        assert state["open_orders"] == [{"type": "BUY"}]

    def test_has_timestamp(self, tmp_dirs):
        rm.update_status("X")
        state = rm.get_state()
        assert "timestamp" in state
        assert isinstance(state["timestamp"], float)

    def test_survives_corrupt_existing_file(self, tmp_dirs):
        """If existing state file is corrupt, should still write new state."""
        with open(tmp_dirs["state_file"], "w") as f:
            f.write("{{{broken")
        rm.update_status("Recovery", "Recovered")
        state = rm.get_state()
        assert state["phase"] == "Recovery"


# =========================================================================
# get_high_water_marks / save_high_water_marks
# =========================================================================

class TestHighWaterMarks:
    """Tests for HWM load/save cycle."""

    def test_empty_when_no_state(self, tmp_dirs):
        hwm = rm.get_high_water_marks()
        assert hwm == {}

    def test_save_and_load_roundtrip(self, tmp_dirs):
        rm.update_status("Init")  # ensure state file exists
        rm.save_high_water_marks({"US123": 8.5, "DE456": 3.2})
        hwm = rm.get_high_water_marks()
        assert hwm["US123"] == 8.5
        assert hwm["DE456"] == 3.2

    def test_save_preserves_other_state(self, tmp_dirs):
        rm.update_status("Active", balance=5000.0, portfolio=[{"name": "X"}])
        rm.save_high_water_marks({"US123": 10.0})
        state = rm.get_state()
        assert state["phase"] == "Active"
        assert state["balance"] == 5000.0
        assert state["portfolio"] == [{"name": "X"}]
        assert state["high_water_marks"] == {"US123": 10.0}

    def test_overwrite_hwms(self, tmp_dirs):
        rm.update_status("Init")
        rm.save_high_water_marks({"A": 1.0})
        rm.save_high_water_marks({"B": 2.0})
        hwm = rm.get_high_water_marks()
        assert "A" not in hwm
        assert hwm["B"] == 2.0

    def test_empty_dict_clears_hwms(self, tmp_dirs):
        rm.update_status("Init", high_water_marks={"X": 5.0})
        rm.save_high_water_marks({})
        assert rm.get_high_water_marks() == {}


# =========================================================================
# get_live_logs
# =========================================================================

class TestGetLiveLogs:
    """Tests for get_live_logs() - session log tail reader."""

    def test_returns_placeholder_when_no_file(self, tmp_dirs):
        result = rm.get_live_logs()
        assert "Warte auf Log-Daten" in result

    def test_reads_last_n_lines(self, tmp_dirs):
        with open(tmp_dirs["session_log"], "w") as f:
            for i in range(100):
                f.write(f"Line {i}\n")
        result = rm.get_live_logs(lines=5)
        assert "Line 95" in result
        assert "Line 99" in result
        assert "Line 0" not in result

    def test_reads_all_when_fewer_than_limit(self, tmp_dirs):
        with open(tmp_dirs["session_log"], "w") as f:
            f.write("Only line\n")
        result = rm.get_live_logs(lines=50)
        assert "Only line" in result

    def test_handles_empty_file(self, tmp_dirs):
        with open(tmp_dirs["session_log"], "w") as f:
            f.write("")
        result = rm.get_live_logs()
        assert isinstance(result, str)

    def test_default_lines_is_50(self, tmp_dirs):
        with open(tmp_dirs["session_log"], "w") as f:
            for i in range(200):
                f.write(f"Log {i}\n")
        result = rm.get_live_logs()  # default lines=50
        # Should contain lines 150-199 but not line 0
        assert "Log 199" in result
        assert "Log 0" not in result
