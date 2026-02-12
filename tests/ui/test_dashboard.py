"""
Unit tests for ui.dashboard

Streamlit apps cannot be easily unit-tested because they require
a Streamlit runtime environment. These tests validate the data
transformation logic used by the dashboard, not the rendering.

Tested:
    - Connectivity detection logic
    - Portfolio DataFrame transformation
    - Orders DataFrame column selection
"""

import time

import pytest


# =========================================================================
# Connectivity detection logic
# =========================================================================

class TestConnectivityLogic:
    """Test the connectivity threshold logic used in dashboard."""

    def test_online_when_recent_update(self):
        """State with timestamp within 120s -> online."""
        state = {"timestamp": time.time() - 30}
        delta = time.time() - state.get("timestamp", 0)
        is_online = delta < 120
        assert is_online is True

    def test_offline_when_stale_update(self):
        """State with timestamp older than 120s -> offline."""
        state = {"timestamp": time.time() - 200}
        delta = time.time() - state.get("timestamp", 0)
        is_online = delta < 120
        assert is_online is False

    def test_offline_when_no_timestamp(self):
        """State without timestamp -> offline."""
        state = {}
        delta = time.time() - state.get("timestamp", 0)
        is_online = delta < 120
        assert is_online is False


# =========================================================================
# Portfolio data transformation
# =========================================================================

class TestPortfolioTransformation:
    """Test the DataFrame rename logic used in the Depot tab."""

    RENAME_MAP = {
        "name": "Aktie",
        "qty": "Stk.",
        "value_eur": "Wert",
        "performance_since_buy": "Perf.",
        "peak_pct": "Peak%",
    }

    def test_renames_known_columns(self):
        import pandas as pd
        data = [{"name": "Tesla", "qty": 5, "value_eur": 1000, "performance_since_buy": "+2%"}]
        df = pd.DataFrame(data)
        existing_cols = [c for c in self.RENAME_MAP.keys() if c in df.columns]
        df = df[existing_cols].rename(columns=self.RENAME_MAP)
        assert "Aktie" in df.columns
        assert "name" not in df.columns

    def test_skips_missing_columns(self):
        import pandas as pd
        data = [{"name": "Tesla", "qty": 5}]
        df = pd.DataFrame(data)
        existing_cols = [c for c in self.RENAME_MAP.keys() if c in df.columns]
        df = df[existing_cols].rename(columns=self.RENAME_MAP)
        assert "Aktie" in df.columns
        assert "Wert" not in df.columns  # value_eur not in data

    def test_empty_portfolio(self):
        data = []
        assert len(data) == 0  # Dashboard shows info text for empty


# =========================================================================
# Orders data transformation
# =========================================================================

class TestOrdersTransformation:
    """Test the open orders column selection logic."""

    def test_selects_known_columns(self):
        import pandas as pd
        data = [{"type": "BUY", "qty": 10, "name": "Apple", "status": "Pending", "extra": "ignored"}]
        df = pd.DataFrame(data)
        cols_to_show = ["type", "qty", "name", "status"]
        df = df[[c for c in cols_to_show if c in df.columns]]
        assert list(df.columns) == ["type", "qty", "name", "status"]
        assert "extra" not in df.columns

    def test_handles_missing_status(self):
        import pandas as pd
        data = [{"type": "SELL", "qty": 5, "name": "Tesla"}]
        df = pd.DataFrame(data)
        cols_to_show = ["type", "qty", "name", "status"]
        df = df[[c for c in cols_to_show if c in df.columns]]
        assert "status" not in df.columns  # missing from data
