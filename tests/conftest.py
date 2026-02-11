"""
Shared fixtures for all test modules.
Provides temporary directory isolation so tests never touch real project files.
"""

import os
import pytest


@pytest.fixture
def tmp_dirs(tmp_path):
    """Create isolated temporary directories mirroring the project layout."""
    log_dir = tmp_path / "logs"
    json_dir = tmp_path / "json"
    config_dir = tmp_path / "config"
    log_dir.mkdir()
    json_dir.mkdir()
    config_dir.mkdir()

    return {
        "root": tmp_path,
        "log_dir": str(log_dir),
        "json_dir": str(json_dir),
        "config_dir": str(config_dir),
        "session_log": str(log_dir / "session_live.log"),
        "blacklist_file": str(json_dir / "blacklist_stocks.json"),
        "state_file": str(json_dir / "bot_state.json"),
        "control_file": str(json_dir / "bot_control.json"),
    }
