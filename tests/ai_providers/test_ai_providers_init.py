"""
Unit tests for ai_providers/__init__.py

Functions tested:
    - load_ai_config   (file I/O)
    - save_ai_config   (file I/O)
    - create_provider   (factory - error paths only, no real providers instantiated)
    - PROVIDERS dict    (data integrity)

NOT tested (requires actual API keys / browser):
    - Actual provider instantiation with real credentials
"""

import json
import os

import pytest

import ai_providers as aip


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Redirect CONFIG_DIR and CONFIG_FILE to a temp directory."""
    config_dir = str(tmp_path / "config")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "ai_config.json")
    monkeypatch.setattr(aip, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(aip, "CONFIG_FILE", config_file)
    return {"dir": config_dir, "file": config_file}


# =========================================================================
# PROVIDERS constant
# =========================================================================

class TestProviders:
    """Verify the PROVIDERS dict has expected entries."""

    def test_has_all_five_providers(self):
        expected = {"google_studio", "google_api", "openai", "claude", "ollama"}
        assert set(aip.PROVIDERS.keys()) == expected

    def test_values_are_strings(self):
        for key, val in aip.PROVIDERS.items():
            assert isinstance(val, str)
            assert len(val) > 0


# =========================================================================
# load_ai_config
# =========================================================================

class TestLoadAiConfig:
    """Tests for load_ai_config()."""

    def test_default_when_no_file(self, isolated_config):
        result = aip.load_ai_config()
        assert result == {"provider": "google_studio"}

    def test_reads_existing_config(self, isolated_config):
        data = {"provider": "openai", "openai": {"api_key": "sk-test", "model": "gpt-4o"}}
        with open(isolated_config["file"], "w") as f:
            json.dump(data, f)
        result = aip.load_ai_config()
        assert result["provider"] == "openai"
        assert result["openai"]["api_key"] == "sk-test"

    def test_returns_default_on_corrupt_file(self, isolated_config):
        with open(isolated_config["file"], "w") as f:
            f.write("{{{bad json")
        result = aip.load_ai_config()
        assert result == {"provider": "google_studio"}

    def test_preserves_all_keys(self, isolated_config):
        data = {"provider": "claude", "claude": {"api_key": "x"}, "extra_key": True}
        with open(isolated_config["file"], "w") as f:
            json.dump(data, f)
        result = aip.load_ai_config()
        assert result["extra_key"] is True


# =========================================================================
# save_ai_config
# =========================================================================

class TestSaveAiConfig:
    """Tests for save_ai_config()."""

    def test_creates_file(self, isolated_config):
        aip.save_ai_config({"provider": "ollama"})
        assert os.path.exists(isolated_config["file"])

    def test_roundtrip(self, isolated_config):
        original = {
            "provider": "openai",
            "openai": {"api_key": "sk-123", "model": "gpt-4o"},
        }
        aip.save_ai_config(original)
        loaded = aip.load_ai_config()
        assert loaded == original

    def test_overwrites_existing(self, isolated_config):
        aip.save_ai_config({"provider": "ollama"})
        aip.save_ai_config({"provider": "claude"})
        loaded = aip.load_ai_config()
        assert loaded["provider"] == "claude"

    def test_creates_config_dir_if_missing(self, tmp_path, monkeypatch):
        new_dir = str(tmp_path / "new_config")
        config_file = os.path.join(new_dir, "ai_config.json")
        monkeypatch.setattr(aip, "CONFIG_DIR", new_dir)
        monkeypatch.setattr(aip, "CONFIG_FILE", config_file)
        aip.save_ai_config({"provider": "openai"})
        assert os.path.isdir(new_dir)
        assert os.path.exists(config_file)

    def test_unicode_preserved(self, isolated_config):
        """ensure_ascii=False should preserve special characters."""
        data = {"provider": "ollama", "note": "Umlaute: aou"}
        aip.save_ai_config(data)
        with open(isolated_config["file"], "r", encoding="utf-8") as f:
            raw = f.read()
        assert "Umlaute" in raw


# =========================================================================
# create_provider - error paths
# =========================================================================

class TestCreateProvider:
    """Tests for create_provider() - only error/validation paths.
    We don't instantiate real providers (would need API keys / browser).
    """

    def test_google_studio_requires_browser_context(self, isolated_config):
        aip.save_ai_config({"provider": "google_studio"})
        with pytest.raises(ValueError, match="browser context"):
            aip.create_provider(browser_context=None)

    def test_openai_requires_api_key(self, isolated_config):
        aip.save_ai_config({"provider": "openai", "openai": {"api_key": ""}})
        with pytest.raises(ValueError, match="API Key"):
            aip.create_provider()

    def test_claude_requires_api_key(self, isolated_config):
        aip.save_ai_config({"provider": "claude", "claude": {"api_key": ""}})
        with pytest.raises(ValueError, match="API Key"):
            aip.create_provider()

    def test_google_api_requires_api_key(self, isolated_config):
        aip.save_ai_config({"provider": "google_api", "google_api": {"api_key": ""}})
        with pytest.raises(ValueError, match="API Key"):
            aip.create_provider()

    def test_unknown_provider_raises(self, isolated_config):
        aip.save_ai_config({"provider": "nonexistent_ai"})
        with pytest.raises(ValueError, match="Unbekannter AI Provider"):
            aip.create_provider()

    def test_missing_provider_key_defaults_to_google_studio(self, isolated_config):
        """Config without 'provider' key defaults to google_studio."""
        aip.save_ai_config({})  # no provider key
        with pytest.raises(ValueError, match="browser context"):
            aip.create_provider()  # defaults to google_studio -> needs browser
