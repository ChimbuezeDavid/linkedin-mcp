"""Network and connection outreach tools executing within the authenticated user's account."""

import logging
from typing import Any, Dict, List, Optional

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_type
from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.tools.network")


@require_auth
async def send_connection_request(
    profile_url: str,
    custom_note: str = "",
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Send a LinkedIn connection invitation to a professional from your authenticated account.

    Args:
        profile_url: The target profile URL to connect with.
        custom_note: Optional personalized message (up to 300 characters).

    Returns:
        Status result of the connection request.
    """
    if not profile_url or not profile_url.strip():
        return {"success": False, "error": "EMPTY_URL", "message": "Profile URL is required."}

    target = profile_url.strip()
    if not target.startswith("http"):
        target = f"https://www.linkedin.com/in/{target.strip('/')}/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(target, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Look for primary Connect button
        connect_btn = page.locator("main button:has-text('Connect'), div.pvs-profile-actions button:has-text('Connect')").first
        if await connect_btn.count() == 0:
            # Check More actions dropdown
            more_btn = page.locator("button:has-text('More'), button[aria-label*='More actions']").first
            if await more_btn.count() > 0:
                await more_btn.click()
                await human_delay(0.8, 1.5)
                connect_btn = page.locator("div.artdeco-dropdown__content button:has-text('Connect')").first

        if await connect_btn.count() == 0:
            return {
                "success": False,
                "error": "CONNECT_NOT_AVAILABLE",
                "message": "Connect button not found. You may already be connected or connection is restricted by this user."
            }

        await connect_btn.click()
        await human_delay(1.5, 2.5)

        # Check if invitation modal opens with 'Add a note'
        note_btn = page.locator("button[aria-label*='Add a note'], button:has-text('Add a note')").first
        if custom_note and custom_note.strip() and await note_btn.count() > 0:
            await note_btn.click()
            await human_delay(0.8, 1.5)
            textarea = page.locator("textarea[name='message'], textarea#custom-message").first
            if await textarea.count() > 0:
                await textarea.fill(custom_note.strip()[:300])
                await human_delay(1.0, 2.0)

        # Click send invitation
        send_btn = page.locator("button[aria-label*='Send invitation'], button:has-text('Send'):not([disabled]), button:has-text('Send without a note')").first
        if await send_btn.count() > 0:
            await send_btn.click()
            await human_delay(2.0, 3.5)

        return {
            "success": True,
            "boundary": f"Sent from {account_identity.name if account_identity else 'authenticated user'}'s account",
            "message": "Connection invitation successfully sent.",
            "target": target,
            "with_note": bool(custom_note and custom_note.strip())
        }


@require_auth
async def get_pending_invitations(
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """List pending connection requests received by your authenticated account.

    Returns:
        List of pending invitations with sender name, headline, and profile links.
    """
    url = "https://www.linkedin.com/mynetwork/invitation-manager/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        invitations = []
        cards = page.locator("li.invitation-card, div.invitation-card")
        total = await cards.count()

        for i in range(min(total, 15)):
            card = cards.nth(i)
            try:
                name = ""
                name_elem = card.locator(".invitation-card__title, a[data-control-name='invitee_title']").first
                if await name_elem.count() > 0:
                    name = (await name_elem.inner_text()).strip()

                headline = ""
                headline_elem = card.locator(".invitation-card__subtitle").first
                if await headline_elem.count() > 0:
                    headline = (await headline_elem.inner_text()).strip()

                if name:
                    invitations.append({
                        "sender": name,
                        "headline": headline
                    })
            except Exception as e:
                logger.debug(f"Error parsing invitation card {i}: {e}")

        return {
            "success": True,
            "boundary": f"Read from {account_identity.name if account_identity else 'authenticated user'}'s network",
            "count": len(invitations),
            "invitations": invitations
        }


@require_auth
async def manage_invitation(
    sender_name: str,
    action: str = "accept",
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Accept or ignore an incoming connection invitation on your account.

    Args:
        sender_name: Name of the person whose invitation you want to manage.
        action: Either 'accept' or 'ignore' (default: 'accept').

    Returns:
        Status result of managing the connection invitation.
    """
    if not sender_name or not sender_name.strip():
        return {"success": False, "error": "EMPTY_NAME", "message": "Sender name is required."}

    action_norm = action.strip().lower()
    if action_norm not in ["accept", "ignore"]:
        return {"success": False, "error": "INVALID_ACTION", "message": "Action must be either 'accept' or 'ignore'."}

    url = f"{config.base_url}/mynetwork/invitation-manager/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        cards = page.locator("li.invitation-card, div.invitation-card")
        total = await cards.count()
        matched_card = None

        for i in range(min(total, 20)):
            card = cards.nth(i)
            name_elem = card.locator(".invitation-card__title, a[data-control-name='invitee_title']").first
            if await name_elem.count() > 0:
                name_text = (await name_elem.inner_text()).strip().lower()
                if sender_name.strip().lower() in name_text:
                    matched_card = card
                    break

        if not matched_card:
            return {
                "success": False,
                "error": "INVITATION_NOT_FOUND",
                "message": f"No pending invitation found from '{sender_name}'."
            }

        if action_norm == "accept":
            btn = matched_card.locator("button:has-text('Accept'), button[aria-label*='Accept' i]").first
        else:
            btn = matched_card.locator("button:has-text('Ignore'), button[aria-label*='Ignore' i]").first

        if await btn.count() == 0:
            return {
                "success": False,
                "error": "BUTTON_NOT_FOUND",
                "message": f"Could not find the '{action_norm}' button for '{sender_name}'."
            }

        await btn.click()
        await human_delay(2.0, 3.5)

        return {
            "success": True,
            "boundary": f"Managed on {account_identity.name if account_identity else 'authenticated user'}'s account",
            "message": f"Successfully executed '{action_norm}' on invitation from {sender_name}.",
            "sender": sender_name,
            "action": action_norm
        }
