"""Browser engine managing Playwright lifecycle and contexts."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from linkedin_mcp.config import config
from linkedin_mcp.browser.stealth import apply_stealth, DEFAULT_USER_AGENT

logger = logging.getLogger("linkedin_mcp.browser")


class BrowserManager:
    """Manages Playwright browser instances and contexts."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def get_playwright(self) -> Playwright:
        """Get or start the Playwright instance for the active event loop."""
        current_loop = asyncio.get_running_loop()
        if self._playwright is not None and self._loop != current_loop:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._loop = current_loop
        return self._playwright

    @asynccontextmanager
    async def get_context(
        self,
        headless: Optional[bool] = None,
        use_storage_state: bool = True
    ) -> AsyncGenerator[BrowserContext, None]:
        """Create a managed browser context with stealth configurations."""
        pw = await self.get_playwright()
        is_headless = config.headless if headless is None else headless

        storage_state_arg = None
        if use_storage_state and config.storage_state_file.exists():
            storage_state_arg = str(config.storage_state_file)

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

        launch_kwargs = dict(
            user_data_dir=str(config.browser_profile_dir),
            headless=is_headless,
            slow_mo=config.slow_mo_ms if not is_headless else 0,
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="UTC",
            args=args,
        )

        if config.browser_channel:
            context = await pw.chromium.launch_persistent_context(
                channel=config.browser_channel,
                **launch_kwargs
            )
        else:
            context = await pw.chromium.launch_persistent_context(**launch_kwargs)

        try:
            yield context
        finally:
            try:
                # Save storage state for offline verification
                await context.storage_state(path=str(config.storage_state_file))
            except Exception as e:
                logger.debug(f"Could not export storage state: {e}")
            await context.close()

    @asynccontextmanager
    async def get_page(
        self,
        headless: Optional[bool] = None
    ) -> AsyncGenerator[Page, None]:
        """Convenience helper yielding a stealth-configured page."""
        async with self.get_context(headless=headless) as context:
            pages = context.pages
            page = pages[0] if pages else await context.new_page()
            await apply_stealth(page)
            page.set_default_timeout(config.timeout_ms)
            yield page

    async def close(self) -> None:
        """Shutdown Playwright engine."""
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


browser_manager = BrowserManager()
