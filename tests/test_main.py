"""
Unit tests for main.py

Functions/classes tested:
    - DualLogger       (stdout + file logging)
    - smart_sleep      (interruptible sleep with stop command)
    - run_config_page  (subprocess + signal file workflow)

Note: main_loop is not directly tested (infinite loop).
The module-level DualLogger instantiation is mocked away in tests.
"""

import asyncio
import os
import sys
import time

import pytest
from unittest.mock import MagicMock, patch, mock_open


# =========================================================================
# DualLogger
# =========================================================================

class TestDualLogger:
    """Tests for DualLogger - dual stdout + file writer."""

    def test_creates_log_file(self, tmp_path):
        # Import after setup to avoid module-level side effects
        log_file = str(tmp_path / "logs" / "test.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        from main import DualLogger
        logger = DualLogger(log_file)
        assert os.path.exists(log_file)

    def test_creates_log_directory_if_missing(self, tmp_path):
        log_file = str(tmp_path / "new_dir" / "test.log")

        from main import DualLogger
        logger = DualLogger(log_file)
        assert os.path.isdir(os.path.dirname(log_file))

    def test_writes_to_file(self, tmp_path):
        log_file = str(tmp_path / "logs" / "test.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        from main import DualLogger
        logger = DualLogger(log_file)
        logger.write("Hello World")

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Hello World" in content

    def test_writes_start_marker(self, tmp_path):
        log_file = str(tmp_path / "logs" / "test.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        from main import DualLogger
        logger = DualLogger(log_file)

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "LOG START" in content

    def test_flush_does_not_raise(self, tmp_path):
        log_file = str(tmp_path / "logs" / "test.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        from main import DualLogger
        logger = DualLogger(log_file)
        logger.flush()  # Should not raise


# =========================================================================
# smart_sleep
# =========================================================================

class TestSmartSleep:
    """Tests for smart_sleep() - interruptible sleep with stop detection."""

    @patch("main.remote_manager")
    def test_completes_full_sleep(self, mock_rm):
        mock_rm.get_command.return_value = "run"
        from main import smart_sleep
        result = asyncio.run(smart_sleep(2))
        assert result is True

    @patch("main.remote_manager")
    def test_stops_on_stop_command(self, mock_rm):
        mock_rm.get_command.return_value = "stop"
        from main import smart_sleep
        result = asyncio.run(smart_sleep(10))
        assert result is False

    @patch("main.remote_manager")
    def test_updates_status_periodically(self, mock_rm):
        mock_rm.get_command.return_value = "run"
        from main import smart_sleep
        asyncio.run(smart_sleep(3))
        # update_status called at least once (every 10 iterations)
        assert mock_rm.update_status.call_count >= 1


# =========================================================================
# run_config_page
# =========================================================================

class TestRunConfigPage:
    """Tests for run_config_page() - AI config subprocess workflow."""

    @patch("main.subprocess.Popen")
    @patch("main.CONFIG_DIR")
    def test_returns_true_when_signal_exists(self, mock_dir, mock_popen, tmp_path):
        """When signal file is created, should return True."""
        from main import run_config_page

        config_dir = str(tmp_path)
        signal_file = os.path.join(config_dir, ".start_bot")

        # Mock the config dir
        with patch("main.CONFIG_DIR", config_dir), \
             patch("main.os.path.exists") as mock_exists, \
             patch("main.os.remove"):

            # Simulate: signal file appears after one check
            exists_results = [False, True]  # First call: remove old, Second: signal found
            mock_exists.side_effect = lambda path: (
                exists_results.pop(0) if exists_results and ".start_bot" in path
                else False
            )

            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_proc.terminate = MagicMock()
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc

            result = run_config_page()
            assert result is True

    @patch("main.subprocess.Popen")
    @patch("main.CONFIG_DIR")
    def test_returns_false_when_process_dies(self, mock_dir, mock_popen, tmp_path):
        """When the streamlit process exits, should return False."""
        from main import run_config_page

        config_dir = str(tmp_path)

        with patch("main.CONFIG_DIR", config_dir), \
             patch("main.os.path.exists", return_value=False), \
             patch("main.os.remove"):

            mock_proc = MagicMock()
            mock_proc.poll.return_value = 1  # Process exited
            mock_proc.terminate = MagicMock()
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc

            result = run_config_page()
            assert result is False

    @patch("main.subprocess.Popen")
    def test_terminates_config_process(self, mock_popen, tmp_path):
        """Config process should be terminated after signal received."""
        from main import run_config_page

        config_dir = str(tmp_path)
        signal_file = os.path.join(config_dir, ".start_bot")

        with patch("main.CONFIG_DIR", config_dir), \
             patch("main.os.path.exists") as mock_exists, \
             patch("main.os.remove"):

            call_count = [0]
            def exists_side_effect(path):
                if ".start_bot" in path:
                    call_count[0] += 1
                    return call_count[0] >= 2  # Signal appears on 2nd check
                return False

            mock_exists.side_effect = exists_side_effect

            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_proc.terminate = MagicMock()
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc

            run_config_page()
            mock_proc.terminate.assert_called_once()
