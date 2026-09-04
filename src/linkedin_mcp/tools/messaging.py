"""Direct messaging tools operating exclusively from the authenticated user's inbox."""

import logging
from typing import Any, Dict, List, Optional

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_type
from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.tools.messaging")


@require_auth
async def list_conversations(
    limit: int = 10,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """List recent direct message conversations from your authenticated inbox.

    Args:
        limit: Number of conversation threads to fetch (default: 10, max: 20).

    Returns:
        List of recent conversations with participant name, preview snippet, and time.
    """
    limit = max(1, min(limit, 20))
    messaging_url = "https://www.linkedin.com/messaging/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(messaging_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        conversations: List[Dict[str, Any]] = []
        threads = page.locator("li.msg-conversation-listitem, li.msg-conversation-card")
        total = min(await threads.count(), limit)

        for i in range(total):
            item = threads.nth(i)
            try:
                name = ""
                name_elem = item.locator("h3.msg-conversation-listitem__participant-names, .msg-conversation-card__participant-names").first
                if await name_elem.count() > 0:
                    name = (await name_elem.inner_text()).strip()

                snippet = ""
                snippet_elem = item.locator("p.msg-conversation-card__message-snippet-body, .msg-conversation-listitem__message-snippet").first
                if await snippet_elem.count() > 0:
                    snippet = (await snippet_elem.inner_text()).strip()

                time_str = ""
                time_elem = item.locator("time").first
                if await time_elem.count() > 0:
                    time_str = (await time_elem.inner_text()).strip()

                if name:
                    conversations.append({
                        "participant": name,
                        "latest_message": snippet,
                        "timestamp": time_str
                    })
            except Exception as e:
                logger.debug(f"Error reading conversation thread {i}: {e}")

        return {
            "success": True,
            "boundary": f"Read from {account_identity.name if account_identity else 'authenticated user'}'s inbox",
            "count": len(conversations),
            "conversations": conversations
        }


@require_auth
async def send_message(
    recipient_profile_url: str,
    message_text: str,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Send a direct message to a LinkedIn member from your authenticated account.

    Args:
        recipient_profile_url: Profile URL of the person to message (e.g. 'https://www.linkedin.com/in/username').
        message_text: The message body to send.

    Returns:
        Status result indicating whether the message was dispatched.
    """
    if not recipient_profile_url or not recipient_profile_url.strip():
        return {"success": False, "error": "EMPTY_RECIPIENT", "message": "Recipient profile URL is required."}

    if not message_text or not message_text.strip():
        return {"success": False, "error": "EMPTY_MESSAGE", "message": "Message text cannot be empty."}

    target = recipient_profile_url.strip()
    if not target.startswith("http"):
        target = f"https://www.linkedin.com/in/{target.strip('/')}/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(target, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Look for the primary "Message" button on profile
        message_btn = page.locator("main button:has-text('Message'), div.entry-point button:has-text('Message')").first
        if await message_btn.count() == 0:
            # Check inside 'More' actions dropdown
            more_btn = page.locator("button:has-text('More'), button[aria-label*='More actions']").first
            if await more_btn.count() > 0:
                await more_btn.click()
                await human_delay(0.8, 1.5)
                message_btn = page.locator("div.artdeco-dropdown__content button:has-text('Message')").first

        if await message_btn.count() == 0:
            return {
                "success": False,
                "error": "CANNOT_MESSAGE",
                "message": "Message button not found. You may not be connected or InMail may be required for this member."
            }

        await message_btn.click()
        await human_delay(1.5, 2.5)

        # Find the message compose box
        editor = page.locator(
            "div.msg-form__contenteditable[contenteditable='true'], "
            "div[role='textbox'][aria-label*='Write a message' i]"
        ).first

        if await editor.count() == 0:
            return {
                "success": False,
                "error": "EDITOR_NOT_FOUND",
                "message": "Messaging compose window did not open."
            }

        await editor.click()
        await human_delay(0.5, 1.0)
        await editor.fill(message_text.strip())
        await human_delay(1.0, 2.0)

        # Find send button
        send_btn = page.locator("button.msg-form__send-button:not([disabled]), button[type='submit']:has-text('Send')").first
        if await send_btn.count() == 0:
            return {
                "success": False,
                "error": "SEND_BUTTON_DISABLED",
                "message": "Send button could not be activated."
            }

        await send_btn.click()
        await human_delay(2.0, 3.5)

        return {
            "success": True,
            "boundary": f"Sent from {account_identity.name if account_identity else 'authenticated user'}'s account",
            "message": "Direct message sent successfully.",
            "recipient": target
        }


@require_auth
async def get_conversation_messages(
    recipient_name: str,
    limit: int = 15,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Retrieve full chronological message history with a specific connection from your inbox.

    Args:
        recipient_name: Name of the contact or keyword to locate the conversation thread.
        limit: Maximum number of recent messages to retrieve from the thread (default: 15).

    Returns:
        List of chronological messages showing author, message body, and timestamp.
    """
    if not recipient_name or not recipient_name.strip():
        return {"success": False, "error": "EMPTY_RECIPIENT", "message": "Recipient name is required."}

    target_name = recipient_name.strip().lower()
    limit = max(1, min(limit, 30))
    messaging_url = f"{config.base_url}/messaging/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(messaging_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Find thread item directly from visible conversation list
        threads = page.locator("li.msg-conversation-listitem, li.msg-conversation-card, div.msg-conversation-card")
        total = await threads.count()
        thread_item = None

        for i in range(total):
            item = threads.nth(i)
            item_text = (await item.inner_text()).lower()
            if target_name in item_text:
                thread_item = item
                break

        # Fallback to search input if not in initial visible list
        if not thread_item:
            search_input = page.locator("input.msg-conversations-container__search-input, input[placeholder*='Search messages' i]").first
            if await search_input.count() > 0:
                await search_input.fill(recipient_name.strip())
                await search_input.press("Enter")
                await human_delay(1.5, 2.5)

                search_threads = page.locator("li.msg-conversation-listitem, li.msg-conversation-card")
                if await search_threads.count() > 0:
                    thread_item = search_threads.first

        if not thread_item:
            return {
                "success": False,
                "error": "THREAD_NOT_FOUND",
                "message": f"Could not find any messaging thread matching '{recipient_name}'."
            }

        await thread_item.click()
        await human_delay(1.5, 3.0)

        # Scrape messages in active thread
        messages: List[Dict[str, Any]] = []
        msg_elements = page.locator("li.msg-s-message-list__event, div.msg-s-event-listitem")
        total_msgs = await msg_elements.count()
        start_idx = max(0, total_msgs - limit)

        for i in range(start_idx, total_msgs):
            elem = msg_elements.nth(i)
            try:
                sender = ""
                sender_elem = elem.locator(".msg-s-message-group__name, .msg-s-message-group__profile-link").first
                if await sender_elem.count() > 0:
                    sender = (await sender_elem.inner_text()).strip()

                body = ""
                body_elem = elem.locator("p.msg-s-event-listitem__body").first
                if await body_elem.count() > 0:
                    body = (await body_elem.inner_text()).strip()

                timestamp = ""
                time_elem = elem.locator("time.msg-s-message-group__timestamp, time").first
                if await time_elem.count() > 0:
                    timestamp = (await time_elem.inner_text()).strip()

                if body:
                    messages.append({
                        "sender": sender or "Participant",
                        "text": body,
                        "timestamp": timestamp
                    })
            except Exception as e:
                logger.debug(f"Error parsing message {i}: {e}")

        return {
            "success": True,
            "boundary": f"Inbox thread for {account_identity.name if account_identity else 'authenticated user'}",
            "contact": recipient_name,
            "message_count": len(messages),
            "messages": messages
        }
