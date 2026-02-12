"""
Unit tests for services.browser_utils

Functions tested:
    - check_soft_crash        (crash detection & reload)
    - create_browser_context  (browser launch with correct config)

All Playwright interactions are mocked.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.browser_utils import check_soft_crash, create_browser_context


def _run(coro):
    """Run async coroutine in sync test."""
    return asyncio.run(coro)


# =========================================================================
# check_soft_crash
# =========================================================================

class TestCheckSoftCrash:
    """Tests for check_soft_crash() - Chromium crash detection."""

    def test_no_crash_returns_false(self):
        page = AsyncMock()
        page.title = AsyncMock(return_value="OON Boersespiel")
        locator = AsyncMock()
        locator.count = AsyncMock(return_value=0)
        h1_locator = MagicMock()
        h1_locator.filter = MagicMock(return_value=locator)
        page.locator = MagicMock(return_value=h1_locator)

        assert _run(check_soft_crash(page)) is False

    def test_crash_in_title_returns_true(self):
        page = AsyncMock()
        page.title = AsyncMock(return_value="Aw, Snap!")
        page.reload = AsyncMock()
        page.wait_for_load_state = AsyncMock()

        assert _run(check_soft_crash(page)) is True
        page.reload.assert_called_once()

    def test_crash_in_header_returns_true(self):
        page = AsyncMock()
        page.title = AsyncMock(return_value="Normal Title")
        page.reload = AsyncMock()
        page.wait_for_load_state = AsyncMock()

        crash_el = AsyncMock()
        crash_el.count = AsyncMock(return_value=1)
        crash_el.first = AsyncMock()
        crash_el.first.is_visible = AsyncMock(return_value=True)

        h1_locator = MagicMock()
        h1_locator.filter = MagicMock(return_value=crash_el)
        page.locator = MagicMock(return_value=h1_locator)

        assert _run(check_soft_crash(page)) is True

    def test_no_crash_header_not_visible(self):
        page = AsyncMock()
        page.title = AsyncMock(return_value="Normal Title")

        crash_el = AsyncMock()
        crash_el.count = AsyncMock(return_value=1)
        crash_el.first = AsyncMock()
        crash_el.first.is_visible = AsyncMock(return_value=False)

        h1_locator = MagicMock()
        h1_locator.filter = MagicMock(return_value=crash_el)
        page.locator = MagicMock(return_value=h1_locator)

        assert _run(check_soft_crash(page)) is False

    def test_exception_in_title_propagates(self):
        """Non-crash exceptions in page.title() should propagate."""
        page = AsyncMock()
        page.title = AsyncMock(side_effect=RuntimeError("disconnected"))

        with pytest.raises(RuntimeError, match="disconnected"):
            _run(check_soft_crash(page))

    def test_header_check_exception_swallowed(self):
        """Exceptions during header check are swallowed (bare except)."""
        page = AsyncMock()
        page.title = AsyncMock(return_value="Normal Title")

        h1_locator = MagicMock()
        h1_locator.filter = MagicMock(side_effect=Exception("stale"))
        page.locator = MagicMock(return_value=h1_locator)

        assert _run(check_soft_crash(page)) is False


# =========================================================================
# create_browser_context
# =========================================================================

class TestCreateBrowserContext:
    """Tests for create_browser_context() - browser setup."""

    @patch("services.browser_utils.config")
    def test_returns_context(self, mock_config):
        mock_config.USER_DATA_DIR = "/tmp/session"
        mock_config.BROWSER_SHOW = True

        mock_context = AsyncMock()
        mock_context.set_default_timeout = MagicMock()

        playwright = MagicMock()
        playwright.chromium.launch_persistent_context = AsyncMock(
            return_value=mock_context
        )

        result = _run(create_browser_context(playwright))
        assert result == mock_context

    @patch("services.browser_utils.config")
    def test_headless_when_browser_show_false(self, mock_config):
        mock_config.USER_DATA_DIR = "/tmp/session"
        mock_config.BROWSER_SHOW = False

        mock_context = AsyncMock()
        mock_context.set_default_timeout = MagicMock()

        playwright = MagicMock()
        playwright.chromium.launch_persistent_context = AsyncMock(
            return_value=mock_context
        )

        _run(create_browser_context(playwright))
        call_kwargs = playwright.chromium.launch_persistent_context.call_args
        assert call_kwargs.kwargs.get("headless") is True or call_kwargs[1].get("headless") is True

    @patch("services.browser_utils.config")
    def test_headed_when_browser_show_true(self, mock_config):
        mock_config.USER_DATA_DIR = "/tmp/session"
        mock_config.BROWSER_SHOW = True

        mock_context = AsyncMock()
        mock_context.set_default_timeout = MagicMock()

        playwright = MagicMock()
        playwright.chromium.launch_persistent_context = AsyncMock(
            return_value=mock_context
        )

        _run(create_browser_context(playwright))
        call_kwargs = playwright.chromium.launch_persistent_context.call_args
        assert call_kwargs.kwargs.get("headless") is False or call_kwargs[1].get("headless") is False

    @patch("services.browser_utils.config")
    def test_sets_default_timeout(self, mock_config):
        mock_config.USER_DATA_DIR = "/tmp/session"
        mock_config.BROWSER_SHOW = False

        mock_context = AsyncMock()
        mock_context.set_default_timeout = MagicMock()

        playwright = MagicMock()
        playwright.chromium.launch_persistent_context = AsyncMock(
            return_value=mock_context
        )

        _run(create_browser_context(playwright))
        mock_context.set_default_timeout.assert_called_once_with(15000)

    @patch("services.browser_utils.config")
    def test_uses_chrome_channel(self, mock_config):
        mock_config.USER_DATA_DIR = "/tmp/session"
        mock_config.BROWSER_SHOW = False

        mock_context = AsyncMock()
        mock_context.set_default_timeout = MagicMock()

        playwright = MagicMock()
        playwright.chromium.launch_persistent_context = AsyncMock(
            return_value=mock_context
        )

        _run(create_browser_context(playwright))
        call_kwargs = playwright.chromium.launch_persistent_context.call_args
        assert call_kwargs.kwargs.get("channel") == "chrome" or call_kwargs[1].get("channel") == "chrome"
