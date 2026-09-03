"""Authentication and account identity manager."""

import asyncio
import json
import logging
import shutil
import time
from typing import Optional
from pydantic import BaseModel, Field
from playwright.async_api import Page

from linkedin_mcp.config import config
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay

logger = logging.getLogger("linkedin_mcp.auth")


class AccountIdentity(BaseModel):
    """Details of the authenticated user whose account owns this session."""

    name: str = Field(description="Full name of the authenticated user")
    vanity_name: str = Field(description="Profile vanity slug (e.g. 'john-doe')")
    profile_url: str = Field(description="Canonical profile URL")
    headline: Optional[str] = Field(default=None, description="Profile headline")
    last_verified: float = Field(default_factory=time.time)
    is_authenticated: bool = True


class AuthManager:
    """Handles session checks, interactive login, and identity resolution."""

    def __init__(self) -> None:
        self._cached_identity: Optional[AccountIdentity] = None

    def get_cached_identity(self) -> Optional[AccountIdentity]:
        """Load cached identity if available."""
        if self._cached_identity:
            return self._cached_identity

        if config.account_identity_file.exists():
            try:
                data = json.loads(config.account_identity_file.read_text(encoding="utf-8"))
                self._cached_identity = AccountIdentity(**data)
                return self._cached_identity
            except Exception as e:
                logger.warning(f"Failed to read cached identity: {e}")

        return None

    def save_identity(self, identity: AccountIdentity) -> None:
        """Cache the resolved identity to disk."""
        self._cached_identity = identity
        config.account_identity_file.write_text(
            identity.model_dump_json(indent=2),
            encoding="utf-8"
        )

    async def verify_session(self, page: Page) -> Optional[AccountIdentity]:
        """Navigate to LinkedIn and verify if session is authenticated."""
        try:
            # Go to /in/me/ which redirects to the user's specific profile
            await page.goto(config.my_profile_url, wait_until="domcontentloaded", timeout=25000)
            await human_delay(1.5, 3.0)

            current_url = page.url

            # If redirected to login, authwall, or checkpoint
            if any(path in current_url for path in ["/login", "/authwall", "/uas/login", "/checkpoint"]):
                logger.info(f"Session is not authenticated (URL: {current_url})")
                return None

            # Successfully reached own profile
            if "/in/" in current_url:
                # Extract vanity name from redirected URL
                # Example: https://www.linkedin.com/in/jane-doe-123/ -> jane-doe-123
                parts = current_url.split("/in/")[-1].strip("/").split("?")[0].split("/")
                vanity_name = parts[0] if parts else "me"

                # Extract user's name
                name = ""
                name_elem = page.locator("h1").first
                if await name_elem.count() > 0:
                    name = (await name_elem.inner_text()).strip()

                if not name:
                    name = vanity_name

                # Extract headline
                headline = None
                headline_elem = page.locator(".text-body-medium.break-words").first
                if await headline_elem.count() > 0:
                    headline = (await headline_elem.inner_text()).strip()

                clean_profile_url = f"https://www.linkedin.com/in/{vanity_name}/"

                identity = AccountIdentity(
                    name=name,
                    vanity_name=vanity_name,
                    profile_url=clean_profile_url,
                    headline=headline,
                    last_verified=time.time(),
                    is_authenticated=True,
                )
                self.save_identity(identity)
                return identity

            # Fallback: check if we are on feed
            if "/feed" in current_url:
                # Try navigating to /in/me/ once more
                await page.goto(config.my_profile_url, wait_until="domcontentloaded", timeout=20000)
                await human_delay(1.5, 2.5)
                return await self.verify_session(page)

            return None

        except Exception as e:
            logger.error(f"Error verifying session: {e}")
            return None

    async def start_interactive_login(self, timeout_seconds: int = 300) -> dict:
        """Launch a headed browser for the user to log in interactively."""
        logger.info("Starting interactive login...")

        async with browser_manager.get_page(headless=False) as page:
            await page.goto(config.login_url, wait_until="domcontentloaded")

            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                current_url = page.url

                # Check if user reached feed or profile
                if any(x in current_url for x in ["/feed", "/in/"]):
                    logger.info("Login detected! Resolving account identity...")
                    await human_delay(2.0, 3.0)
                    identity = await self.verify_session(page)
                    if identity:
                        return {
                            "status": "success",
                            "message": f"Successfully authenticated as {identity.name} ({identity.profile_url})",
                            "identity": identity.model_dump(),
                        }

                await asyncio.sleep(2)

            return {
                "status": "timeout",
                "message": f"Interactive login timed out after {timeout_seconds} seconds. Please try again.",
            }

    def logout(self) -> dict:
        """Clear all stored session state, browser profile, and cached identity."""
        self._cached_identity = None

        if config.account_identity_file.exists():
            config.account_identity_file.unlink()

        if config.storage_state_file.exists():
            config.storage_state_file.unlink()

        if config.browser_profile_dir.exists():
            try:
                shutil.rmtree(config.browser_profile_dir)
            except Exception as e:
                logger.warning(f"Could not delete browser profile directory: {e}")

        config.ensure_directories()

        return {
            "status": "logged_out",
            "message": "All session data, cookies, and identity caches have been cleared."
        }


auth_manager = AuthManager()
