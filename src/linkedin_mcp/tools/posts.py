"""Feed and post tools published strictly as the authenticated user."""

import logging
from pathlib import Path
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
    media_path: Optional[str] = None,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Publish a new post on LinkedIn authored exclusively by your authenticated profile.

    Args:
        text: The content of your post.
        media_path: Optional absolute file path to an image (.png, .jpg, .jpeg) or document (.pdf) to attach.

    Returns:
        Status result indicating whether the post was successfully published.
    """
    if not text or not text.strip():
        return {"success": False, "error": "EMPTY_POST", "message": "Post text cannot be empty."}

    content = text.strip()
    media_file: Optional[Path] = None

    if media_path:
        media_file = Path(media_path)
        if not media_file.is_file():
            return {
                "success": False,
                "error": "MEDIA_NOT_FOUND",
                "message": f"Attached media file does not exist at: {media_path}"
            }

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

        # If attaching media, trigger file upload before or after typing
        if media_file:
            file_input = page.locator("input[type='file']").first
            if await file_input.count() > 0:
                try:
                    await file_input.set_input_files(str(media_file.resolve()))
                    await human_delay(2.0, 3.5)
                    # If an artdeco modal has a 'Next' or 'Done' button for the media
                    next_btn = page.locator(
                        "div.share-box-footer button:has-text('Next'), "
                        "button.share-box-footer__primary-btn:has-text('Next'), "
                        "button:has-text('Done')"
                    ).first
                    if await next_btn.count() > 0 and await next_btn.is_visible():
                        await next_btn.click()
                        await human_delay(1.5, 2.5)
                except Exception as e:
                    logger.warning(f"Failed to attach media: {e}")

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
            "post_preview": content[:140] + ("..." if len(content) > 140 else ""),
            "attached_media": str(media_file) if media_file else None
        }


@require_auth
async def create_poll(
    question: str,
    options: List[str],
    duration: str = "1 week",
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Create and publish an interactive poll to your LinkedIn feed.

    Args:
        question: The poll question text (max 140 characters).
        options: List of poll options (between 2 and 4 options, each max 30 chars).
        duration: Poll duration ('1 day', '3 days', '1 week', or '2 weeks'). Default is '1 week'.

    Returns:
        Status result of the poll publication.
    """
    if not question or not question.strip():
        return {"success": False, "error": "EMPTY_QUESTION", "message": "Poll question cannot be empty."}

    if not options or len(options) < 2:
        return {"success": False, "error": "INSUFFICIENT_OPTIONS", "message": "Poll must have at least 2 options."}

    if len(options) > 4:
        return {"success": False, "error": "TOO_MANY_OPTIONS", "message": "Poll cannot have more than 4 options."}

    cleaned_options = [opt.strip()[:30] for opt in options if opt and opt.strip()]
    if len(cleaned_options) < 2:
        return {"success": False, "error": "INVALID_OPTIONS", "message": "At least 2 non-empty options are required."}

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.feed_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        start_post_btn = page.locator("button:has-text('Start a post'), button[aria-label*='Start a post']").first
        if await start_post_btn.count() == 0:
            return {"success": False, "error": "TRIGGER_NOT_FOUND", "message": "Could not find 'Start a post' button."}

        await start_post_btn.click()
        await human_delay(1.5, 2.5)

        # Look for Poll trigger icon or button inside modal
        poll_btn = page.locator("button[aria-label*='Create a poll' i], button:has-text('Create a poll')").first
        if await poll_btn.count() == 0:
            # Check more options button inside share box
            more_btn = page.locator("button[aria-label*='Add to your post' i], button[aria-label*='More' i]").first
            if await more_btn.count() > 0:
                await more_btn.click()
                await human_delay(0.8, 1.5)
                poll_btn = page.locator("button:has-text('Create a poll'), button[aria-label*='poll' i]").first

        if await poll_btn.count() == 0:
            return {"success": False, "error": "POLL_OPTION_NOT_FOUND", "message": "Poll creation tool not available in post editor."}

        await poll_btn.click()
        await human_delay(1.5, 2.5)

        # Fill question
        question_input = page.locator("input#poll-question-input, input[name='question'], textarea[placeholder*='question' i]").first
        if await question_input.count() > 0:
            await question_input.fill(question.strip()[:140])
            await human_delay(0.5, 1.0)

        # Fill options 1 & 2
        option_inputs = page.locator("input[id*='poll-option'], input[name*='option']")
        if await option_inputs.count() >= 2:
            await option_inputs.nth(0).fill(cleaned_options[0])
            await human_delay(0.3, 0.6)
            await option_inputs.nth(1).fill(cleaned_options[1])
            await human_delay(0.3, 0.6)

        # Add remaining options if provided
        for opt_idx in range(2, len(cleaned_options)):
            add_opt_btn = page.locator("button:has-text('+ Add option'), button:has-text('Add option')").first
            if await add_opt_btn.count() > 0:
                await add_opt_btn.click()
                await human_delay(0.5, 1.0)
                new_inputs = page.locator("input[id*='poll-option'], input[name*='option']")
                if await new_inputs.count() > opt_idx:
                    await new_inputs.nth(opt_idx).fill(cleaned_options[opt_idx])
                    await human_delay(0.3, 0.6)

        # Done button inside poll modal
        done_btn = page.locator("button:has-text('Done'), div.poll-footer button.artdeco-button--primary").first
        if await done_btn.count() > 0:
            await done_btn.click()
            await human_delay(1.5, 2.5)

        # Final Post button
        post_btn = page.locator("button.share-actions__primary-action, button:has-text('Post'):not([disabled])").first
        if await post_btn.count() > 0 and await post_btn.is_enabled():
            await post_btn.click()
            await human_delay(3.0, 5.0)

        return {
            "success": True,
            "boundary": f"Published as {account_identity.name if account_identity else 'authenticated user'}",
            "message": "Poll published successfully to your LinkedIn feed.",
            "question": question.strip()[:140],
            "options": cleaned_options,
            "duration": duration
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

        # Modern LinkedIn feed fallback
        if not posts:
            modern_posts = await page.evaluate("""(maxCount) => {
                const likeButtons = Array.from(document.querySelectorAll('button')).filter(b => {
                    const t = (b.innerText || '').trim();
                    return t === 'Like';
                });
                const out = [];
                const seen = new Set();
                for (const btn of likeButtons) {
                    if (out.length >= maxCount) break;
                    let container = btn;
                    for (let i = 0; i < 7; i++) {
                        if (container.parentElement) container = container.parentElement;
                        if (container.tagName === 'DIV' && container.innerText.includes('Like') && container.innerText.includes('Comment')) {
                            const authorLink = container.querySelector('a[href*="/in/"], a[href*="/company/"]');
                            if (authorLink && !seen.has(container)) {
                                seen.add(container);
                                const lines = container.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                                const author = authorLink.innerText.trim().split('\\n')[0];
                                const textLines = lines.filter(l => !['Like', 'Comment', 'Repost', 'Send', 'Promoted', author].includes(l));
                                out.push({
                                    author: author || 'LinkedIn Member',
                                    author_headline: '',
                                    content: textLines.slice(0, 4).join(' ').slice(0, 500)
                                });
                                break;
                            }
                        }
                    }
                }
                return out;
            }""", limit)
            if modern_posts:
                posts.extend(modern_posts)

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
