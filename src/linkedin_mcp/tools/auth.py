"""Authentication tools for checking status, interactive login, and logout."""

import logging
from typing import Any, Dict

from linkedin_mcp.config import config
from linkedin_mcp.auth.manager import auth_manager
from linkedin_mcp.browser.engine import browser_manager

logger = logging.getLogger("linkedin_mcp.tools.auth")


async def linkedin_login_status() -> Dict[str, Any]:
    """Check the current LinkedIn authentication status and retrieve verified user details.

    Returns:
        A dictionary containing:
        - is_authenticated (bool): Whether a valid authenticated session exists.
        - user (dict, optional): The authenticated user's name, vanity_name, profile_url, and headline.
        - message (str): Human-readable status description.
    """
    cached = auth_manager.get_cached_identity()
    if cached:
        return {
            "is_authenticated": True,
            "status": "AUTHENTICATED",
            "account_boundary": f"Locked to {cached.name} ({cached.profile_url})",
            "user": cached.model_dump(),
            "message": f"Active session verified for {cached.name} ({cached.profile_url})."
        }

    # If no session file exists, we are definitely unauthenticated
    if not config.storage_state_file.exists():
        return {
            "is_authenticated": False,
            "status": "UNAUTHENTICATED",
            "account_boundary": "NONE",
            "user": None,
            "message": (
                "Not authenticated. No actions can be performed without an active session. "
                "Please invoke 'linkedin_start_login' to log in."
            )
        }

    # Verify live
    try:
        async with browser_manager.get_page(headless=True) as page:
            identity = await auth_manager.verify_session(page)
            if identity:
                return {
                    "is_authenticated": True,
                    "status": "AUTHENTICATED",
                    "account_boundary": f"Locked to {identity.name} ({identity.profile_url})",
                    "user": identity.model_dump(),
                    "message": f"Session active and verified for {identity.name}."
                }
    except Exception as e:
        logger.warning(f"Error checking live login status: {e}")

    return {
        "is_authenticated": False,
        "status": "UNAUTHENTICATED",
        "account_boundary": "NONE",
        "user": None,
        "message": (
            "Not authenticated. No actions can be performed without an active session. "
            "Please invoke 'linkedin_start_login' to log in."
        )
    }


async def linkedin_start_login(timeout_seconds: int = 300) -> Dict[str, Any]:
    """Open an interactive browser window on your screen to log in to LinkedIn.

    Use this tool to sign in, complete two-factor authentication (2FA), or resolve security verification.
    Once you log in and reach the LinkedIn feed or your profile, the session will be securely saved.

    Args:
        timeout_seconds: Maximum time in seconds to wait for login completion (default: 300).

    Returns:
        Result dictionary indicating success or timeout, along with verified account details.
    """
    return await auth_manager.start_interactive_login(timeout_seconds=timeout_seconds)


async def linkedin_logout() -> Dict[str, Any]:
    """Log out of LinkedIn and clear all stored session cookies, cache, and identity data.

    Returns:
        Confirmation that the session has been reset.
    """
    return auth_manager.logout()
