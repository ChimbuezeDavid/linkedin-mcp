"""Feed and post tools published strictly as the authenticated user."""

import logging
from typing import Any, Dict, List, Optional

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_scroll, human_type
from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.tools.posts")


@require_auth
async def create_post(
    text: str,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Publish a new post on LinkedIn authored exclusively by your authenticated profile.

    Args:
        text: The content of your post.

    Returns:
        Status result indicating whether the post was successfully published.
    """
    if not text or not text.strip():
        return {"success": False, "error": "EMPTY_POST", "message": "Post text cannot be empty."}

    content = text.strip()

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.feed_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Look for "Start a post" button
        start_post_btn = page.locator(
            "button:has-text('Start a post'), "
            "button.share-box-feed-entry__trigger, "
            "button[aria-label*='Start a post']"
        ).first

        if await start_post_btn.count() == 0:
            return {
                "success": False,
                "error": "TRIGGER_NOT_FOUND",
                "message": "Could not find the 'Start a post' button on your feed."
            }

        await start_post_btn.click()
        await human_delay(1.5, 2.5)

        # Locate editor modal
        editor = page.locator(
            "div.ql-editor[contenteditable='true'], "
            "div[role='textbox'][aria-label*='post' i], "
            "div.editor-content div[contenteditable='true']"
        ).first

        if await editor.count() == 0:
            return {
                "success": False,
                "error": "EDITOR_NOT_FOUND",
                "message": "Could not locate the post text editor modal."
            }

        await editor.click()
        await human_delay(0.5, 1.0)
        # Type the post content
        await editor.fill(content)
        await human_delay(1.5, 2.5)

        # Click the Post button
        post_btn = page.locator(
            "button.share-actions__primary-action, "
            "button:has-text('Post'):not([disabled]), "
            "div.share-box_actions button.artdeco-button--primary"
        ).first

        if await post_btn.count() == 0 or not await post_btn.is_enabled():
            return {
                "success": False,
                "error": "POST_BUTTON_DISABLED",
                "message": "Post button was not enabled or could not be found."
            }

        await post_btn.click()
        await human_delay(3.0, 5.0)

        return {
            "success": True,
            "boundary": f"Published as {account_identity.name if account_identity else 'authenticated user'}",
            "message": "Post successfully published to your LinkedIn feed.",
            "post_preview": content[:140] + ("..." if len(content) > 140 else "")
        }


@require_auth
async def get_feed(
    limit: int = 5,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Read recent posts from your personal LinkedIn feed.

    Args:
        limit: Number of posts to retrieve (default: 5, max: 15).

    Returns:
        List of feed posts with author name, headline, post text, and links.
    """
    limit = max(1, min(limit, 15))

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.feed_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)
        await human_scroll(page, scrolls=2, distance=400)

        posts = []
        post_elements = page.locator("div.feed-shared-update-v2, div[data-urn*='activity']")
        count = min(await post_elements.count(), limit)

        for i in range(count):
            elem = post_elements.nth(i)
            try:
                # Author
                author = ""
                author_elem = elem.locator("span.feed-shared-actor__name, span.update-components-actor__name").first
                if await author_elem.count() > 0:
                    author = (await author_elem.inner_text()).strip()

                # Author description / headline
                author_headline = ""
                sub_elem = elem.locator("span.feed-shared-actor__description, span.update-components-actor__description").first
                if await sub_elem.count() > 0:
                    author_headline = (await sub_elem.inner_text()).strip()

                # Post text content
                text = ""
                text_elem = elem.locator("div.feed-shared-update-v2__description, div.update-components-text").first
                if await text_elem.count() > 0:
                    text = (await text_elem.inner_text()).strip()

                if author or text:
                    posts.append({
                        "author": author,
                        "author_headline": author_headline,
                        "content": text[:500] + ("..." if len(text) > 500 else ""),
                    })
            except Exception as e:
                logger.debug(f"Error parsing feed item {i}: {e}")

        return {
            "success": True,
            "boundary": f"Viewed from {account_identity.name if account_identity else 'authenticated'}'s feed",
            "count": len(posts),
            "posts": posts
        }


@require_auth
async def comment_on_post(
    post_url: str,
    comment_text: str,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Leave a comment on a LinkedIn post as the authenticated user.

    Args:
        post_url: The URL of the LinkedIn post.
        comment_text: The comment text to post.

    Returns:
        Status result of the comment operation.
    """
    if not comment_text or not comment_text.strip():
        return {"success": False, "error": "EMPTY_COMMENT", "message": "Comment cannot be empty."}

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(post_url.strip(), wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Find comment box
        comment_box = page.locator("div.comments-comment-box__editor, div.ql-editor[aria-label*='comment' i]").first
        if await comment_box.count() == 0:
            # Click the comment trigger button first if collapsed
            trigger = page.locator("button[aria-label*='Comment' i]").first
            if await trigger.count() > 0:
                await trigger.click()
                await human_delay(1.0, 2.0)
                comment_box = page.locator("div.comments-comment-box__editor, div.ql-editor").first

        if await comment_box.count() == 0:
            return {"success": False, "error": "COMMENT_BOX_NOT_FOUND", "message": "Could not locate the comment input box."}

        await comment_box.click()
        await comment_box.fill(comment_text.strip())
        await human_delay(1.0, 2.0)

        # Click submit
        submit_btn = page.locator("button.comments-comment-box__submit-button:not([disabled])").first
        if await submit_btn.count() == 0:
            return {"success": False, "error": "SUBMIT_NOT_FOUND", "message": "Could not find active submit button."}

        await submit_btn.click()
        await human_delay(2.0, 3.5)

        return {
            "success": True,
            "boundary": f"Commented as {account_identity.name if account_identity else 'authenticated user'}",
            "message": "Comment successfully submitted.",
            "comment": comment_text.strip()
        }
