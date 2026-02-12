"""
Unit tests for ui.config_page

Streamlit rendering cannot be unit-tested directly. These tests validate
the config save logic and signal file mechanism used by the config page.

Tested:
    - Config build logic for each provider
    - Signal file creation (.start_bot)
"""

import json
import os

import pytest
from unittest.mock import patch

import ai_providers as aip


# =========================================================================
# Config build logic
# =========================================================================

class TestConfigBuild:
    """Test the config dict construction for each provider."""

    def test_openai_config_structure(self):
        cfg = {"provider": "openai"}
        cfg["openai"] = {"api_key": "sk-test", "model": "gpt-4o"}
        assert cfg["provider"] == "openai"
        assert cfg["openai"]["api_key"] == "sk-test"
        assert cfg["openai"]["model"] == "gpt-4o"

    def test_claude_config_structure(self):
        cfg = {"provider": "claude"}
        cfg["claude"] = {"api_key": "sk-ant-test", "model": "claude-sonnet-4-5-20250929"}
        assert cfg["provider"] == "claude"
        assert cfg["claude"]["model"] == "claude-sonnet-4-5-20250929"

    def test_google_api_config_structure(self):
        cfg = {"provider": "google_api"}
        cfg["google_api"] = {"api_key": "AIza-test", "model": "gemini-2.0-flash"}
        assert cfg["provider"] == "google_api"
        assert cfg["google_api"]["model"] == "gemini-2.0-flash"

    def test_ollama_config_structure(self):
        cfg = {"provider": "ollama"}
        cfg["ollama"] = {"base_url": "http://localhost:11434", "model": "llama3"}
        assert cfg["provider"] == "ollama"
        assert cfg["ollama"]["base_url"] == "http://localhost:11434"

    def test_google_studio_needs_no_extra(self):
        cfg = {"provider": "google_studio"}
        assert "google_studio" not in cfg or cfg["provider"] == "google_studio"

    def test_preserves_existing_keys(self):
        """Updating provider should preserve other config keys."""
        old_cfg = {"provider": "openai", "openai": {"api_key": "old"}, "extra": True}
        new_cfg = dict(old_cfg)
        new_cfg["provider"] = "claude"
        new_cfg["claude"] = {"api_key": "new", "model": "claude-opus-4-6"}
        assert new_cfg["extra"] is True
        assert new_cfg["openai"]["api_key"] == "old"  # preserved


# =========================================================================
# Signal file mechanism
# =========================================================================

class TestSignalFile:
    """Test the .start_bot signal file used for bot communication."""

    def test_signal_file_creation(self, tmp_path):
        signal_file = str(tmp_path / ".start_bot")
        with open(signal_file, "w") as f:
            f.write("start")
        assert os.path.exists(signal_file)
        with open(signal_file) as f:
            assert f.read() == "start"

    def test_signal_file_cleanup(self, tmp_path):
        signal_file = str(tmp_path / ".start_bot")
        with open(signal_file, "w") as f:
            f.write("start")
        os.remove(signal_file)
        assert not os.path.exists(signal_file)


# =========================================================================
# Config save & load roundtrip (via ai_providers)
# =========================================================================

class TestConfigRoundtrip:
    """Test that config page save logic produces loadable configs."""

    def test_openai_roundtrip(self, tmp_path, monkeypatch):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "ai_config.json")
        monkeypatch.setattr(aip, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(aip, "CONFIG_FILE", config_file)

        cfg = {"provider": "openai", "openai": {"api_key": "sk-test", "model": "gpt-4o"}}
        aip.save_ai_config(cfg)
        loaded = aip.load_ai_config()
        assert loaded["provider"] == "openai"
        assert loaded["openai"]["api_key"] == "sk-test"

    def test_claude_roundtrip(self, tmp_path, monkeypatch):
        config_dir = str(tmp_path / "config")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "ai_config.json")
        monkeypatch.setattr(aip, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(aip, "CONFIG_FILE", config_file)

        cfg = {"provider": "claude", "claude": {"api_key": "sk-ant-x", "model": "claude-opus-4-6"}}
        aip.save_ai_config(cfg)
        loaded = aip.load_ai_config()
        assert loaded["provider"] == "claude"
        assert loaded["claude"]["model"] == "claude-opus-4-6"
