"""Self-Profile management tools strictly locked to the authenticated user's profile."""

import logging
from typing import Any, Dict, Optional

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_scroll, human_type
from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.tools.self_profile")


@require_auth
async def get_my_profile(account_identity: AccountIdentity = None) -> Dict[str, Any]:
    """Retrieve full profile information for the authenticated user's own profile.

    This tool is strictly locked to your own account and reads your current headline,
    about section, experiences, and skills.

    Returns:
        Dictionary containing your profile details.
    """
    async with browser_manager.get_page(headless=True) as page:
        # Strictly navigate to own profile
        await page.goto(config.my_profile_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Extract name
        name = ""
        name_locator = page.locator("h1").first
        if await name_locator.count() > 0:
            name = (await name_locator.inner_text()).strip()

        # Extract headline
        headline = ""
        headline_locator = page.locator(".text-body-medium.break-words").first
        if await headline_locator.count() > 0:
            headline = (await headline_locator.inner_text()).strip()

        # Extract location
        location = ""
        location_locator = page.locator("span.text-body-small.inline.t-black--light.break-words").first
        if await location_locator.count() > 0:
            location = (await location_locator.inner_text()).strip()

        # Extract About summary
        about = ""
        about_section = page.locator("section:has(#about)")
        if await about_section.count() > 0:
            about_text_elem = about_section.locator(".display-flex.ph5.pv3, div.inline-show-more-text").first
            if await about_text_elem.count() > 0:
                about = (await about_text_elem.inner_text()).strip()

        # Extract experience snippets
        experiences = []
        exp_section = page.locator("section:has(#experience)")
        if await exp_section.count() > 0:
            items = exp_section.locator("li.artdeco-list__item")
            count = min(await items.count(), 10)
            for i in range(count):
                item = items.nth(i)
                text = (await item.inner_text()).strip()
                if text:
                    experiences.append(text.replace("\n\n", "\n"))

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "profile_url": page.url,
            "name": name or (account_identity.name if account_identity else "Me"),
            "headline": headline,
            "location": location,
            "about": about,
            "recent_experience_count": len(experiences),
            "experiences": experiences,
        }


@require_auth
async def update_my_headline(headline: str, account_identity: AccountIdentity = None) -> Dict[str, Any]:
    """Update the headline on your own LinkedIn profile.

    Security & Boundary Notice: This tool can ONLY modify your own profile. It does not accept
    a target profile URL and executes strictly within your authenticated account.

    Args:
        headline: The new headline text to display under your name.

    Returns:
        Status result indicating whether the headline update succeeded.
    """
    if not headline or not headline.strip():
        return {
            "success": False,
            "error": "EMPTY_HEADLINE",
            "message": "Headline text cannot be empty."
        }

    headline = headline.strip()

    async with browser_manager.get_page(headless=True) as page:
        # Navigate strictly to /in/me/
        await page.goto(config.my_profile_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Look for the intro edit button
        edit_button = page.locator("button[aria-label*='Edit intro'], button[aria-label*='Edit profile']").first
        if await edit_button.count() == 0:
            # Fallback: look for pencil button in the top profile card
            edit_button = page.locator("main section:first-of-type button:has(svg[data-test-icon='pencil-small'])").first

        if await edit_button.count() == 0:
            return {
                "success": False,
                "error": "BUTTON_NOT_FOUND",
                "message": "Could not find the Edit Intro button on your profile page."
            }

        await edit_button.click()
        await human_delay(1.5, 2.5)

        # In the modal, locate the headline input field
        modal = page.locator("div.artdeco-modal")
        if await modal.count() == 0:
            return {
                "success": False,
                "error": "MODAL_NOT_OPENED",
                "message": "Profile edit modal did not open."
            }

        # Find headline field
        headline_input = modal.locator(
            "input[id*='headline'], textarea[id*='headline'], "
            "div:has(label:has-text('Headline')) input, "
            "div:has(label:has-text('Headline')) textarea"
        ).first

        if await headline_input.count() == 0:
            return {
                "success": False,
                "error": "INPUT_NOT_FOUND",
                "message": "Could not locate the headline input field in the edit modal."
            }

        await human_type(headline_input, headline)
        await human_delay(1.0, 2.0)

        # Click Save
        save_btn = modal.locator("button:has-text('Save'), button.artdeco-button--primary").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate the Save button in the modal."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

        # Verify modal closed
        if await modal.count() > 0 and await modal.is_visible():
            # Check for validation error messages
            error_msg = modal.locator(".artdeco-inline-feedback--error").first
            if await error_msg.count() > 0:
                err_text = (await error_msg.inner_text()).strip()
                return {
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": f"LinkedIn rejected the headline update: {err_text}"
                }

        # Update cached identity if headline changed
        if account_identity:
            account_identity.headline = headline
            from linkedin_mcp.auth.manager import auth_manager
            auth_manager.save_identity(account_identity)

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "message": "Successfully updated your LinkedIn headline.",
            "new_headline": headline
        }


@require_auth
async def update_my_about(summary: str, account_identity: AccountIdentity = None) -> Dict[str, Any]:
    """Update the About / summary section on your own LinkedIn profile.

    Security & Boundary Notice: This tool can ONLY modify your own profile. It executes
    strictly within your authenticated account.

    Args:
        summary: The new summary/bio text for your About section.

    Returns:
        Status result indicating whether the About section update succeeded.
    """
    if not summary or not summary.strip():
        return {
            "success": False,
            "error": "EMPTY_SUMMARY",
            "message": "About/Summary text cannot be empty."
        }

    summary = summary.strip()

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.my_profile_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        about_section = page.locator("section:has(#about)")
        if await about_section.count() == 0:
            return {
                "success": False,
                "error": "ABOUT_SECTION_NOT_FOUND",
                "message": "Could not locate the About section on your profile. You may need to add it manually first."
            }

        # Click pencil button in the about section
        edit_btn = about_section.locator("button[aria-label*='Edit about'], button:has(svg[data-test-icon='pencil-small'])").first
        if await edit_btn.count() == 0:
            return {
                "success": False,
                "error": "EDIT_BUTTON_NOT_FOUND",
                "message": "Could not find the Edit button in your About section."
            }

        await edit_btn.click()
        await human_delay(1.5, 2.5)

        modal = page.locator("div.artdeco-modal")
        if await modal.count() == 0:
            return {
                "success": False,
                "error": "MODAL_NOT_OPENED",
                "message": "About edit modal did not open."
            }

        textarea = modal.locator("textarea").first
        if await textarea.count() == 0:
            return {
                "success": False,
                "error": "TEXTAREA_NOT_FOUND",
                "message": "Could not locate the summary textarea in the modal."
            }

        # Clear and fill text
        await textarea.click()
        await page.keyboard.press("ControlOrMeta+a")
        await page.keyboard.press("Backspace")
        await human_delay(0.5, 1.0)
        # Use fill for longer about blocks, then humanize focus
        await textarea.fill(summary)
        await human_delay(1.0, 2.0)

        save_btn = modal.locator("button:has-text('Save'), button.artdeco-button--primary").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate the Save button in the modal."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "message": "Successfully updated your LinkedIn About section.",
            "summary_preview": summary[:120] + ("..." if len(summary) > 120 else "")
        }
