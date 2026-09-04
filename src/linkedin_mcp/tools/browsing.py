"""Browsing, search, and profile exploration tools running within the authenticated session."""

import logging
import urllib.parse
from typing import Any, Dict, List, Optional

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_scroll

logger = logging.getLogger("linkedin_mcp.tools.browsing")


@require_auth
async def search_people(
    keywords: str,
    location: str = "",
    current_company: str = "",
    limit: int = 10,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Search for people on LinkedIn through your authenticated account.

    The search results reflect your personal network visibility (1st, 2nd, 3rd+ degree connections).

    Args:
        keywords: Search term (e.g. name, job title, skills, e.g. "Senior Software Engineer").
        location: Optional geographical filter (e.g. "United States", "London").
        current_company: Optional current company name filter.
        limit: Maximum number of profiles to return (default: 10, max: 25).

    Returns:
        List of matching profiles with name, headline, location, connection degree, and profile URL.
    """
    if not keywords or not keywords.strip():
        return {"success": False, "error": "EMPTY_QUERY", "message": "Search keywords cannot be empty."}

    limit = max(1, min(limit, 25))
    encoded_keywords = urllib.parse.quote_plus(keywords.strip())
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_keywords}&origin=GLOBAL_SEARCH_HEADER"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(search_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)
        await human_scroll(page, scrolls=2, distance=300)

        results: List[Dict[str, Any]] = []

        # Find result containers
        cards = page.locator("li.reusable-search__result-container, div.entity-result")
        total_found = await cards.count()

        for i in range(min(total_found, limit)):
            card = cards.nth(i)
            try:
                # Extract profile link and name
                title_elem = card.locator("span.entity-result__title-text a, a.app-aware-link").first
                name = ""
                profile_url = ""
                if await title_elem.count() > 0:
                    name = (await title_elem.inner_text()).strip().split("\n")[0]
                    raw_href = await title_elem.get_attribute("href") or ""
                    profile_url = raw_href.split("?")[0]

                # Extract degree badge (e.g. 1st, 2nd, 3rd)
                degree = ""
                badge_elem = card.locator(".entity-result__badge-text, span.image-text-lockup__badge-fallback").first
                if await badge_elem.count() > 0:
                    degree = (await badge_elem.inner_text()).strip()

                # Extract headline/subline
                headline = ""
                headline_elem = card.locator(".entity-result__primary-subtitle, div.linked-area .t-14.t-black").first
                if await headline_elem.count() > 0:
                    headline = (await headline_elem.inner_text()).strip()

                # Extract location
                card_location = ""
                loc_elem = card.locator(".entity-result__secondary-subtitle").first
                if await loc_elem.count() > 0:
                    card_location = (await loc_elem.inner_text()).strip()

                if name and profile_url:
                    results.append({
                        "name": name,
                        "degree": degree,
                        "headline": headline,
                        "location": card_location,
                        "profile_url": profile_url
                    })
            except Exception as e:
                logger.debug(f"Error parsing search result card {i}: {e}")

        # Modern LinkedIn fallback
        if not results:
            modern_results = await page.evaluate("""(maxCount) => {
                const out = [];
                const seen = new Set();
                const buttons = Array.from(document.querySelectorAll('button')).filter(b => {
                    const t = (b.innerText || '').trim();
                    const a = (b.getAttribute('aria-label') || '').trim();
                    return t.includes('Connect') || t.includes('Follow') || t.includes('Message') ||
                           a.includes('Connect') || a.includes('Follow') || a.includes('Message');
                });
                for (const btn of buttons) {
                    if (out.length >= maxCount) break;
                    let container = btn;
                    for (let i = 0; i < 6; i++) {
                        if (container.parentElement) container = container.parentElement;
                        const link = container.querySelector('a[href*="/in/"]');
                        if (link) {
                            const href = link.href.split('?')[0];
                            if (!seen.has(href)) {
                                seen.add(href);
                                const lines = container.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                                const rawHeader = lines[0] || '';
                                const parts = rawHeader.split('•').map(s => s.trim());
                                const name = parts[0] || '';
                                const degree = parts[1] || '';
                                const headline = lines[1] || '';
                                const loc = lines[2] || '';
                                out.push({
                                    name,
                                    degree,
                                    headline,
                                    location: loc,
                                    profile_url: href
                                });
                            }
                            break;
                        }
                    }
                }
                return out;
            }""", limit)
            if modern_results:
                results.extend(modern_results)

        return {
            "success": True,
            "boundary": f"Searched as {account_identity.name if account_identity else 'authenticated user'}",
            "query": keywords,
            "count": len(results),
            "results": results
        }


@require_auth
async def view_profile(
    profile_url: str,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """View another LinkedIn member's profile as your authenticated user.

    Strictly read-only: This tool only reads public and network-visible information.

    Args:
        profile_url: Full LinkedIn profile URL (e.g. 'https://www.linkedin.com/in/username') or vanity handle.

    Returns:
        Structured profile data including name, headline, about, and visible experiences.
    """
    if not profile_url or not profile_url.strip():
        return {"success": False, "error": "EMPTY_URL", "message": "Profile URL cannot be empty."}

    # Normalize profile URL
    target = profile_url.strip()
    if not target.startswith("http"):
        target = f"https://www.linkedin.com/in/{target.strip('/')}/"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(target, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Check for profile not found or authwall
        if "authwall" in page.url:
            return {
                "success": False,
                "error": "AUTHWALL",
                "message": "LinkedIn redirected to an authwall. Profile may be private or inaccessible."
            }

        # Extract name (modern LinkedIn uses h2 in top section, fallback to h1)
        name = ""
        name_elem = page.locator("main section:first-of-type h2, h1").first
        if await name_elem.count() > 0:
            name = (await name_elem.inner_text()).strip()

        # Extract headline (modern LinkedIn uses first p in top section, fallback to .text-body-medium)
        headline = ""
        headline_elem = page.locator("main section:first-of-type p:first-of-type, .text-body-medium.break-words").first
        if await headline_elem.count() > 0:
            headline = (await headline_elem.inner_text()).strip()

        # Extract location (modern LinkedIn uses second p in top section, fallback to .text-body-small)
        location = ""
        loc_elem = page.locator("main section:first-of-type p:nth-of-type(2), span.text-body-small.inline.t-black--light.break-words").first
        if await loc_elem.count() > 0:
            location = (await loc_elem.inner_text()).strip()

        # Extract about
        about = await page.evaluate("""() => {
            const h2 = Array.from(document.querySelectorAll('h2')).find(h => h.innerText.trim() === 'About');
            if (!h2) return '';
            let el = h2.parentElement;
            for (let i = 0; i < 5; i++) {
                if (el && el.innerText.length > 30) {
                    const clone = el.cloneNode(true);
                    const h = clone.querySelector('h2');
                    if (h) h.remove();
                    return clone.innerText.trim();
                }
                el = el ? el.parentElement : null;
            }
            return '';
        }""")

        # Extract experiences
        await human_scroll(page, scrolls=2, distance=400)
        experiences = []
        exp_section = page.locator("section:has(#experience)")
        if await exp_section.count() > 0:
            items = exp_section.locator("li.artdeco-list__item")
            count = min(await items.count(), 6)
            for i in range(count):
                text = (await items.nth(i).inner_text()).strip()
                if text:
                    experiences.append(text.replace("\n\n", "\n"))

        return {
            "success": True,
            "boundary": f"Viewed as {account_identity.name if account_identity else 'authenticated user'}",
            "profile_url": page.url,
            "name": name,
            "headline": headline,
            "location": location,
            "about": about,
            "experiences": experiences
        }
