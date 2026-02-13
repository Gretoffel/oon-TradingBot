"""
Unit tests for core.blacklist

Functions tested:
    - load_blacklist
    - save_blacklist
    - add_to_blacklist
"""

import json
import os

import pytest

from core.blacklist import (
    add_to_blacklist,
    load_blacklist,
    save_blacklist,
)


class TestBlacklist:
    """Tests for the blacklist management functions."""

    def test_load_empty_when_file_missing(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        assert load_blacklist() == []

    def test_save_and_load_roundtrip(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.blacklist.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        data = [{"id": "US123", "reason": "Not tradeable", "date": "2026-01-01"}]
        save_blacklist(data)
        loaded = load_blacklist()
        assert loaded == data

    def test_load_returns_empty_for_dict_format(self, tmp_dirs, monkeypatch):
        """Old format was a dict - should gracefully return empty list."""
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        with open(tmp_dirs["blacklist_file"], "w") as f:
            json.dump({"old": "format"}, f)
        assert load_blacklist() == []

    def test_load_returns_empty_for_corrupted_file(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        with open(tmp_dirs["blacklist_file"], "w") as f:
            f.write("{{{corrupt json")
        assert load_blacklist() == []

    def test_add_to_blacklist_creates_entry(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.blacklist.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist("US999", "Test reason")
        loaded = load_blacklist()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "US999"
        assert loaded[0]["reason"] == "Test reason"
        assert "date" in loaded[0]

    def test_add_to_blacklist_no_duplicates(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.blacklist.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist("US999", "First")
        add_to_blacklist("US999", "Second")
        loaded = load_blacklist()
        assert len(loaded) == 1

    def test_add_to_blacklist_ignores_none(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.blacklist.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist(None)
        add_to_blacklist("")
        add_to_blacklist("N/A")
        assert not os.path.exists(tmp_dirs["blacklist_file"])

    def test_add_multiple_different_entries(self, tmp_dirs, monkeypatch):
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE",
                            tmp_dirs["blacklist_file"])
        monkeypatch.setattr("core.blacklist.config.JSON_DIR",
                            tmp_dirs["json_dir"])
        add_to_blacklist("US111", "Reason A")
        add_to_blacklist("US222", "Reason B")
        loaded = load_blacklist()
        assert len(loaded) == 2

    def test_save_creates_json_dir_if_missing(self, tmp_path, monkeypatch):
        new_dir = str(tmp_path / "new_json")
        bl_file = os.path.join(new_dir, "blacklist.json")
        monkeypatch.setattr("core.blacklist.config.BLACKLIST_FILE", bl_file)
        monkeypatch.setattr("core.blacklist.config.JSON_DIR", new_dir)
        save_blacklist([{"id": "X", "reason": "test", "date": "now"}])
        assert os.path.isdir(new_dir)
        assert os.path.exists(bl_file)
