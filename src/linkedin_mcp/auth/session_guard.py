"""Session Guard enforcing the Authenticated Account Boundary for all tools."""

import functools
import logging
from typing import Any, Callable, Coroutine, Optional
from playwright.async_api import Page

from linkedin_mcp.auth.manager import auth_manager, AccountIdentity
from linkedin_mcp.browser.engine import browser_manager

logger = logging.getLogger("linkedin_mcp.guard")


class UnauthenticatedError(Exception):
    """Raised when an action is attempted without an active authenticated session."""
    pass


async def ensure_authenticated_session(page: Optional[Page] = None) -> AccountIdentity:
    """Validate that an active authenticated session exists.

    If not cached or if verified page is provided, verifies against LinkedIn live.
    Raises UnauthenticatedError if session is not authenticated.
    """
    cached = auth_manager.get_cached_identity()

    if page is not None:
        live_identity = await auth_manager.verify_session(page)
        if live_identity is None:
            raise UnauthenticatedError(
                "Your LinkedIn session is not authenticated or has expired. "
                "Please run 'linkedin_start_login' to log in to your account."
            )
        return live_identity

    if cached is not None and cached.is_authenticated:
        return cached

    # If no session file exists at all, we are definitely unauthenticated
    from linkedin_mcp.config import config
    if not config.storage_state_file.exists():
        raise UnauthenticatedError(
            "No authenticated LinkedIn account found. All actions are restricted "
            "to the authenticated user's account boundary. "
            "Please call 'linkedin_start_login' to sign in to your profile first."
        )

    # Attempt live verification if session file exists
    async with browser_manager.get_page(headless=True) as check_page:
        live_identity = await auth_manager.verify_session(check_page)
        if live_identity is None:
            raise UnauthenticatedError(
                "Your LinkedIn session has expired or is invalid. "
                "Please call 'linkedin_start_login' to sign in to your profile again."
            )
        return live_identity


def require_auth(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator enforcing that the tool executes exclusively within an authenticated account boundary."""
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            # Enforce boundary check
            identity = await ensure_authenticated_session()
            # If the tool takes an 'identity' kwarg, provide it
            if "account_identity" in func.__code__.co_varnames:
                kwargs["account_identity"] = identity
            return await func(*args, **kwargs)
        except UnauthenticatedError as e:
            return {
                "success": False,
                "error": "AUTHENTICATION_REQUIRED",
                "boundary_status": "BLOCKED_UNAUTHENTICATED",
                "message": str(e),
                "instruction": "Call the 'linkedin_start_login' tool to authenticate your account."
            }
        except Exception as e:
            logger.exception(f"Error executing account-bound tool {func.__name__}: {e}")
            return {
                "success": False,
                "error": type(e).__name__,
                "message": f"Operation failed: {str(e)}"
            }

    return wrapper
