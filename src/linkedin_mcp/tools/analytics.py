"""Analytics and performance metrics tools strictly for the authenticated user's profile."""

import logging
from typing import Any, Dict, List, Optional

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_scroll
from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.tools.analytics")


@require_auth
async def get_post_analytics(
    limit: int = 5,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Retrieve engagement metrics and performance data for your recent LinkedIn posts.

    Security Notice: Strictly reads analytics for your authenticated account's recent activity.

    Args:
        limit: Number of recent posts to analyze (default: 5, max: 15).

    Returns:
        List of your recent posts with impressions, reactions, and comments counts.
    """
    limit = max(1, min(limit, 15))
    activity_url = f"{config.base_url}/in/me/recent-activity/all/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(activity_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)
        await human_scroll(page, scrolls=2, distance=400)

        posts_analytics: List[Dict[str, Any]] = []
        post_items = page.locator("div.profile-creator-shared-feed-update__container, div.feed-shared-update-v2, div[data-urn*='activity']")
        total = min(await post_items.count(), limit)

        for i in range(total):
            item = post_items.nth(i)
            try:
                # Post content snippet
                text = ""
                text_elem = item.locator(".feed-shared-update-v2__description, .update-components-text").first
                if await text_elem.count() > 0:
                    text = (await text_elem.inner_text()).strip()

                # Impressions
                impressions = "Not displayed"
                imp_elem = item.locator("span:has-text('impressions'), span:has-text('views'), button[aria-label*='impressions' i]").first
                if await imp_elem.count() > 0:
                    impressions = (await imp_elem.inner_text()).strip()

                # Reactions
                reactions = "0"
                react_elem = item.locator(".social-details-social-counts__reactions-count, button[aria-label*='reaction' i]").first
                if await react_elem.count() > 0:
                    reactions = (await react_elem.inner_text()).strip()

                # Comments
                comments = "0"
                comm_elem = item.locator("button[aria-label*='comment' i], .social-details-social-counts__comments").first
                if await comm_elem.count() > 0:
                    comments = (await comm_elem.inner_text()).strip()

                posts_analytics.append({
                    "post_snippet": text[:150] + ("..." if len(text) > 150 else ""),
                    "impressions": impressions,
                    "reactions": reactions,
                    "comments": comments
                })
            except Exception as e:
                logger.debug(f"Error parsing post analytics item {i}: {e}")

        return {
            "success": True,
            "boundary": f"Analyzed activity for {account_identity.name if account_identity else 'authenticated user'}",
            "count": len(posts_analytics),
            "analytics": posts_analytics
        }


@require_auth
async def get_profile_views(
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Retrieve profile views analytics and viewer demographic insights for your account.

    Security Notice: Strictly queries the authenticated user's private profile analytics.

    Returns:
        Summary of profile view count and top demographic insights.
    """
    analytics_url = f"{config.base_url}/analytics/profile-views/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(analytics_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        total_views = "Data unavailable"
        time_period = "past 90 days"
        viewer_insights: List[str] = []

        # Find headline view count
        view_counter = page.locator("p.analytics-entry-point-card__highlight-text, span.analytics-highlight-text, h2[aria-label*='views' i]").first
        if await view_counter.count() > 0:
            total_views = (await view_counter.inner_text()).strip()

        # Fallback view counter locator
        if total_views == "Data unavailable":
            alt_counter = page.locator("div.analytics-hero-card, div.me-analytics-highlight-card").first
            if await alt_counter.count() > 0:
                total_views = (await alt_counter.inner_text()).replace("\n", " ").strip()

        # Top demographic / viewer insights
        insight_items = page.locator("ul.analytics-entity-list li, div.analytics-insights-card")
        item_count = min(await insight_items.count(), 5)
        for i in range(item_count):
            try:
                txt = (await insight_items.nth(i).inner_text()).strip()
                if txt:
                    viewer_insights.append(txt.replace("\n", " - "))
            except Exception:
                pass

        return {
            "success": True,
            "boundary": f"Profile views for {account_identity.name if account_identity else 'authenticated user'}",
            "total_profile_views": total_views,
            "period": time_period,
            "viewer_demographics": viewer_insights
        }
