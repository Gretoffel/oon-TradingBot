"""
Unit tests for services.oon_service

Functions tested:
    - login       (browser navigation & form filling)
    - scan_depot  (depot page parsing)

All Playwright page interactions are mocked via AsyncMock.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from services.oon_service import login, scan_depot


def _run(coro):
    """Run async coroutine in sync test."""
    return asyncio.run(coro)


@pytest.fixture
def mock_page():
    """Create a mock Playwright page with common async methods."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.is_visible = AsyncMock(return_value=False)
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    page.wait_for_selector = AsyncMock()

    # Default: locator returns empty results
    empty_locator = AsyncMock()
    empty_locator.all = AsyncMock(return_value=[])
    page.locator = MagicMock(return_value=empty_locator)

    return page


# =========================================================================
# login
# =========================================================================

class TestLogin:
    """Tests for login() - browser authentication."""

    @patch("services.oon_service.remote_manager")
    def test_navigates_to_login_url(self, mock_rm, mock_page):
        _run(login(mock_page))
        mock_page.goto.assert_called_once()

    @patch("services.oon_service.remote_manager")
    def test_fills_credentials_when_form_visible(self, mock_rm, mock_page):
        mock_page.is_visible = AsyncMock(return_value=True)
        _run(login(mock_page))
        assert mock_page.fill.call_count == 2

    @patch("services.oon_service.remote_manager")
    def test_presses_enter_after_fill(self, mock_rm, mock_page):
        mock_page.is_visible = AsyncMock(return_value=True)
        _run(login(mock_page))
        mock_page.keyboard.press.assert_called_with("Enter")

    @patch("services.oon_service.remote_manager")
    def test_skips_fill_when_not_visible(self, mock_rm, mock_page):
        mock_page.is_visible = AsyncMock(return_value=False)
        _run(login(mock_page))
        mock_page.fill.assert_not_called()

    @patch("services.oon_service.remote_manager")
    def test_handles_goto_exception(self, mock_rm, mock_page):
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))
        _run(login(mock_page))  # Should not raise

    @patch("services.oon_service.remote_manager")
    def test_tries_cookie_banner_dismiss(self, mock_rm, mock_page):
        """Cookie banner click is attempted (may fail silently)."""
        mock_page.is_visible = AsyncMock(return_value=True)
        _run(login(mock_page))
        # click is called at least once (cookie banner attempt)
        assert mock_page.click.call_count >= 1


# =========================================================================
# scan_depot
# =========================================================================

class TestScanDepot:
    """Tests for scan_depot() - depot page parsing."""

    def _make_empty_page(self):
        """Page mock that returns empty locator results for all queries."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock(side_effect=Exception("timeout"))

        empty_locator = AsyncMock()
        empty_locator.all = AsyncMock(return_value=[])
        page.locator = MagicMock(return_value=empty_locator)
        return page

    @patch("services.oon_service.remote_manager")
    def test_returns_required_keys(self, mock_rm):
        page = self._make_empty_page()
        result = _run(scan_depot(page))
        assert "cash" in result
        assert "stocks" in result
        assert "open_orders" in result

    @patch("services.oon_service.remote_manager")
    def test_empty_depot_returns_defaults(self, mock_rm):
        page = self._make_empty_page()
        result = _run(scan_depot(page))
        assert result["cash"] == 0.0
        assert result["stocks"] == []
        assert result["open_orders"] == []

    @patch("services.oon_service.remote_manager")
    def test_navigates_to_depot_url(self, mock_rm):
        page = self._make_empty_page()
        _run(scan_depot(page))
        page.goto.assert_called_once()

    @patch("services.oon_service.remote_manager")
    def test_updates_status_on_start(self, mock_rm):
        page = self._make_empty_page()
        _run(scan_depot(page))
        mock_rm.update_status.assert_called()

    @patch("services.oon_service.remote_manager")
    def test_cash_extraction_from_eur_span(self, mock_rm):
        """When a EUR span with 'Geldkonto' parent is found, cash is extracted."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock(side_effect=Exception("timeout"))

        # Mock cash span
        cash_span = AsyncMock()
        cash_span.inner_text = AsyncMock(return_value="12.345,67 \u20ac")
        parent_el = AsyncMock()
        parent_el.inner_text = AsyncMock(return_value="Geldkonto 12.345,67 \u20ac")
        cash_span.locator = MagicMock(return_value=parent_el)

        # Make locator return different things for different selectors
        eur_locator = AsyncMock()
        eur_locator.all = AsyncMock(return_value=[cash_span])

        empty_locator = AsyncMock()
        empty_locator.all = AsyncMock(return_value=[])

        def locator_side_effect(selector):
            if "data-currency='EUR'" in selector:
                return eur_locator
            return empty_locator

        page.locator = MagicMock(side_effect=locator_side_effect)

        result = _run(scan_depot(page))
        assert result["cash"] == 12345.67

    @patch("services.oon_service.remote_manager")
    def test_handles_scan_exception_gracefully(self, mock_rm):
        """Errors during stock scanning should not crash the function."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock(side_effect=Exception("timeout"))

        # Make stock locator raise
        stock_locator = AsyncMock()
        stock_locator.all = AsyncMock(side_effect=Exception("element detached"))

        eur_locator = AsyncMock()
        eur_locator.all = AsyncMock(return_value=[])

        open_order_locator = AsyncMock()
        open_order_locator.all = AsyncMock(return_value=[])

        def locator_side_effect(selector):
            if "tbody tr" in selector:
                return stock_locator
            if "Offene" in selector:
                return open_order_locator
            mock = AsyncMock()
            mock.all = AsyncMock(return_value=[])
            return mock

        page.locator = MagicMock(side_effect=locator_side_effect)

        result = _run(scan_depot(page))
        assert isinstance(result, dict)
        assert "stocks" in result
