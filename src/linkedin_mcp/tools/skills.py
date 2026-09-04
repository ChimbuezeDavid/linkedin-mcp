"""Agentic skills and executive workflow tools built on top of LinkedIn core capabilities."""

import logging
from typing import Any, Dict, List, Optional

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_scroll
from linkedin_mcp.config import config
from linkedin_mcp.tools.posts import get_feed

logger = logging.getLogger("linkedin_mcp.tools.skills")


@require_auth
async def get_network_briefing(
    limit: int = 10,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Generate an executive morning briefing and trend digest from your LinkedIn feed.

    Analyzes recent posts across your network, highlights active discussions,
    summarizes key themes, and provides conversation starter suggestions.

    Args:
        limit: Number of feed posts to analyze (default: 10, max: 20).

    Returns:
        Structured executive briefing with trending themes, notable posts, and outreach ideas.
    """
    feed_res = await get_feed(limit=limit)
    if not feed_res.get("success"):
        return {
            "success": False,
            "error": "FEED_FETCH_FAILED",
            "message": f"Could not fetch feed for briefing: {feed_res.get('error', 'unknown error')}"
        }

    raw_posts = feed_res.get("posts", [])
    if not raw_posts:
        return {
            "success": True,
            "boundary": f"Briefing for {account_identity.name if account_identity else 'authenticated user'}",
            "summary": "Your feed has no recent unread updates right now.",
            "trending_topics": [],
            "notable_discussions": []
        }

    # Extract keywords and themes
    common_topics = set()
    notable_discussions: List[Dict[str, str]] = []

    keywords_list = [
        "ai", "agent", "llm", "startup", "launch", "hiring", "product", "growth",
        "engineering", "design", "remote", "cloud", "tech", "funding", "market"
    ]

    for p in raw_posts:
        content = p.get("content", "").lower()
        matched = [k for k in keywords_list if k in content]
        for m in matched:
            common_topics.add(m.capitalize())

        author = p.get("author", "Connection")
        snippet = p.get("content", "")
        if len(snippet) > 40:
            notable_discussions.append({
                "contributor": author,
                "headline": p.get("author_headline", ""),
                "topic_snippet": snippet[:200] + ("..." if len(snippet) > 200 else "")
            })

    return {
        "success": True,
        "boundary": f"Morning briefing for {account_identity.name if account_identity else 'authenticated user'}",
        "analyzed_posts_count": len(raw_posts),
        "trending_themes": sorted(list(common_topics)) if common_topics else ["General Tech", "Industry Updates"],
        "notable_discussions": notable_discussions[:6],
        "engagement_suggestion": (
            f"You have {len(raw_posts)} fresh updates in your network. "
            f"Consider commenting on posts from {raw_posts[0].get('author', 'connections')} to boost visibility."
        )
    }


@require_auth
async def analyze_profile_strength(
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Audit your authenticated profile and generate optimization recommendations.

    Security Notice: Strictly audits your own profile (/in/me). Does not accept any target profile URL.

    Returns:
        Scorecard evaluating headline strength, About section impact, and actionable improvements.
    """
    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.my_profile_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Extract current headline
        headline = ""
        headline_elem = page.locator(".text-body-medium.break-words, h2.top-card-layout__headline").first
        if await headline_elem.count() > 0:
            headline = (await headline_elem.inner_text()).strip()

        # Extract About section
        about = ""
        about_elem = page.locator("section[data-section='summary'] div.display-flex, div.pv-about-section, section:has(#about) .inline-show-more-text").first
        if await about_elem.count() > 0:
            about = (await about_elem.inner_text()).strip()

        # Score calculation
        score = 50
        improvements: List[str] = []
        strengths: List[str] = []

        # Headline evaluation
        if headline:
            if len(headline) >= 40:
                score += 20
                strengths.append(f"Headline is detailed ({len(headline)} chars): '{headline}'")
            else:
                score += 10
                improvements.append("Expand your headline beyond your current job title to highlight your core value proposition and key technologies.")
        else:
            improvements.append("Headline is missing or not visible. Add a punchy, keyword-rich headline.")

        # About evaluation
        if about:
            if len(about) >= 150:
                score += 25
                strengths.append(f"About section is comprehensive ({len(about)} characters).")
            else:
                score += 15
                improvements.append("Your About section is brief. Elaborate on your career narrative, key achievements, and current focus.")
        else:
            improvements.append("About section is empty. Add a compelling summary covering your background, expertise, and how to reach you.")

        if score >= 85:
            rating = "Excellent"
        elif score >= 70:
            rating = "Strong"
        else:
            rating = "Needs Attention"

        return {
            "success": True,
            "boundary": f"Profile audit for {account_identity.name if account_identity else 'authenticated user'}",
            "profile_url": account_identity.profile_url if account_identity else config.my_profile_url,
            "profile_strength_score": f"{score}/100",
            "rating": rating,
            "current_headline": headline,
            "about_length": len(about),
            "strengths": strengths,
            "recommended_actions": improvements
        }
