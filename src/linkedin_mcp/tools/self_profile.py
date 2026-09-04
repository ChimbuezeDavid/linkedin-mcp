"""Self-Profile management tools strictly locked to the authenticated user's profile."""

import logging
from typing import Any, Dict, List, Optional

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

        # Extract name (modern LinkedIn uses h2 in top section, fallback to h1)
        name = ""
        name_locator = page.locator("main section:first-of-type h2, h1").first
        if await name_locator.count() > 0:
            name = (await name_locator.inner_text()).strip()

        # Extract headline (modern LinkedIn uses first p in top section, fallback to .text-body-medium)
        headline = ""
        headline_locator = page.locator("main section:first-of-type p:first-of-type, .text-body-medium.break-words").first
        if await headline_locator.count() > 0:
            headline = (await headline_locator.inner_text()).strip()

        # Extract location (modern LinkedIn uses second p in top section, fallback to .text-body-small)
        location = ""
        location_locator = page.locator("main section:first-of-type p:nth-of-type(2), span.text-body-small.inline.t-black--light.break-words").first
        if await location_locator.count() > 0:
            location = (await location_locator.inner_text()).strip()

        # Extract About summary
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
        edit_button = page.locator(
            "button[aria-label*='Edit intro'], "
            "button[aria-label*='Edit profile'], "
            "a[aria-label*='Edit profile'], "
            "button[aria-label='Edit']"
        ).first
        if await edit_button.count() == 0:
            # Fallback: look for pencil button in the top profile card
            edit_button = page.locator("main section:first-of-type button:has(svg[data-test-icon='pencil-small'])").first

        if await edit_button.count() > 0:
            await edit_button.click()
            await human_delay(1.5, 2.5)
        else:
            # Direct navigation fallback to edit intro URL
            vanity = account_identity.vanity_name if account_identity else "me"
            await page.goto(f"https://www.linkedin.com/in/{vanity}/edit/intro/", wait_until="domcontentloaded")
            await human_delay(2.0, 3.0)

        # In the modal or edit page, find headline field
        headline_input = page.locator(
            "div.tiptap.ProseMirror, "
            "div[role='textbox'][contenteditable='true'], "
            "input[id*='headline'], textarea[id*='headline'], "
            "div:has(label:has-text('Headline')) input, "
            "div:has(label:has-text('Headline')) textarea"
        ).first

        if await headline_input.count() == 0:
            return {
                "success": False,
                "error": "INPUT_NOT_FOUND",
                "message": "Could not locate the headline input field on the edit form."
            }

        # Check if contenteditable rich-text editor (TipTap/ProseMirror)
        is_contenteditable = await headline_input.get_attribute("contenteditable") == "true"
        if is_contenteditable:
            await headline_input.click()
            await page.keyboard.press("ControlOrMeta+A")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(headline, delay=15)
        else:
            await human_type(headline_input, headline)
        await human_delay(1.0, 2.0)

        # Click Save
        save_btn = page.locator("button:has-text('Save'), button.artdeco-button--primary").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate the Save button in the modal."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

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

        about_section = page.locator("section:has(#about), section:has(h2:has-text('About'))")
        if await about_section.count() > 0:
            edit_btn = about_section.locator(
                "button[aria-label*='Edit about'], "
                "button:has(svg[data-test-icon='pencil-small']), "
                "button:has(svg)"
            ).first
            if await edit_btn.count() > 0:
                await edit_btn.evaluate("el => el.click()")
                await human_delay(1.5, 2.5)
        else:
            # Add section flow
            add_sec_btn = page.locator("a:has-text('Add section'), button:has-text('Add section')").first
            if await add_sec_btn.count() > 0:
                await add_sec_btn.evaluate("el => el.click()")
                await human_delay(1.5, 2.5)
                add_about = page.locator("p:has-text('Add about'), :text-is('Add about')").first
                if await add_about.count() > 0:
                    await add_about.click()
                    await human_delay(2.0, 3.0)

        # Locate editor
        editor = page.locator(
            "div[role='textbox'][contenteditable='true'], "
            "div.tiptap.ProseMirror, "
            "textarea"
        ).first
        if await editor.count() == 0:
            return {
                "success": False,
                "error": "EDITOR_NOT_FOUND",
                "message": "Could not locate the summary editor in the About modal."
            }

        # Clear and fill text
        await editor.click()
        await page.keyboard.press("ControlOrMeta+a")
        await page.keyboard.press("Backspace")
        await human_delay(0.5, 1.0)

        is_contenteditable = await editor.get_attribute("contenteditable") == "true"
        if is_contenteditable:
            await page.keyboard.insert_text(summary)
        else:
            await editor.fill(summary)
        await human_delay(1.0, 2.0)

        save_btn = page.locator("button:has-text('Save'), button.artdeco-button--primary").first
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


# ==========================================
# Helpers for Modular Profile Sections
# ==========================================

async def _open_add_section_item(page, category: str, item_name: str) -> bool:
    """Helper to open a specific section form from the profile."""
    if "/in/" not in page.url:
        await page.goto(config.my_profile_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

    add_sec_btn = page.locator("a:has-text('Add section'), button:has-text('Add section')").first
    if await add_sec_btn.count() == 0:
        return False

    await add_sec_btn.evaluate("el => el.click()")
    await human_delay(1.5, 2.5)

    # Check if item is already visible inside dialog
    visible = await page.evaluate(f"""() => {{
        const p = Array.from(document.querySelectorAll('dialog p')).find(el => el.innerText.trim() === '{item_name}');
        return p && p.offsetParent !== null;
    }}""")

    if not visible:
        await page.evaluate(f"""() => {{
            const catP = Array.from(document.querySelectorAll('dialog p')).find(p => p.innerText.trim() === '{category}');
            if (catP) catP.parentElement.click();
        }}""")
        await human_delay(1.0, 1.8)

    clicked = await page.evaluate(f"""() => {{
        const itemP = Array.from(document.querySelectorAll('dialog p')).find(p => p.innerText.trim() === '{item_name}');
        if (itemP) {{
            itemP.click();
            return true;
        }}
        return false;
    }}""")
    await human_delay(2.5, 3.5)
    return clicked


async def _fill_typeahead(page, input_locator, text: str) -> None:
    """Fill a typeahead input field and select first suggestion if available."""
    await input_locator.click()
    await page.keyboard.press("ControlOrMeta+A")
    await page.keyboard.press("Backspace")
    await input_locator.type(text, delay=25)
    await human_delay(1.2, 2.0)

    suggestion = page.locator(
        "div[role='listbox'] div[role='option'], "
        "div.basic-typeahead__selectable-list li, "
        "ul.artdeco-typeahead__results-list li, "
        "div.search-typeahead-v2__hit"
    ).first
    if await suggestion.count() > 0 and await suggestion.is_visible():
        await suggestion.click()
        await human_delay(0.5, 1.0)
    else:
        await page.keyboard.press("Enter")
        await human_delay(0.5, 1.0)


async def _set_select_option(select_loc, target: str) -> None:
    """Select option in a <select> element by partial or exact label or value."""
    if not target:
        return
    await select_loc.evaluate("""(sel, target) => {
        const norm = target.trim().toLowerCase();
        for (const opt of sel.options) {
            if (opt.text.trim().toLowerCase().includes(norm) || opt.value.trim().toLowerCase() === norm) {
                sel.value = opt.value;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                break;
            }
        }
    }""", target)
    await human_delay(0.3, 0.6)


# ==========================================
# Full Profile Management Tools
# ==========================================

@require_auth
async def add_education(
    school: str,
    degree: Optional[str] = "",
    field_of_study: Optional[str] = "",
    start_month: Optional[str] = "",
    start_year: Optional[str] = "",
    end_month: Optional[str] = "",
    end_year: Optional[str] = "",
    grade: Optional[str] = "",
    activities: Optional[str] = "",
    description: Optional[str] = "",
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Add an education credential to your own LinkedIn profile.

    Security & Boundary Notice: Strictly locked to your authenticated account.
    Does not accept an external profile URL.

    Args:
        school: Name of university or school (e.g. 'Afe Babalola University').
        degree: Degree type (e.g. 'Bachelor of Science - BSc').
        field_of_study: Area of study (e.g. 'Computer Science', 'Data Analysis').
        start_month: Starting month (e.g. 'September').
        start_year: Starting year (e.g. '2020').
        end_month: Graduation or ending month (e.g. 'June').
        end_year: Graduation or ending year (e.g. '2024').
        grade: GPA, classification, or honors (optional).
        activities: Clubs, societies, sports (optional).
        description: Description of coursework or achievements (optional).

    Returns:
        Status result indicating whether education was added.
    """
    if not school or not school.strip():
        return {
            "success": False,
            "error": "EMPTY_SCHOOL",
            "message": "School name is required."
        }

    async with browser_manager.get_page(headless=True) as page:
        opened = await _open_add_section_item(page, "Core", "Add education")
        if not opened:
            return {
                "success": False,
                "error": "MODAL_NOT_OPENED",
                "message": "Could not open the Add Education form from profile."
            }

        # School (typeahead)
        school_input = page.locator("div:has(label:has-text('School')) input, input[placeholder*='Boston University'], input[id*='school']").first
        if await school_input.count() > 0:
            await _fill_typeahead(page, school_input, school)

        # Degree
        if degree:
            deg_input = page.locator("div:has(label:has-text('Degree')) input, input[placeholder*='Bachelor of Science'], input[id*='degree']").first
            if await deg_input.count() > 0:
                await _fill_typeahead(page, deg_input, degree)

        # Field of study
        if field_of_study:
            field_input = page.locator("div:has(label:has-text('Field of study')) input, input[placeholder*='Business'], input[id*='fieldOfStudy']").first
            if await field_input.count() > 0:
                await _fill_typeahead(page, field_input, field_of_study)

        # Dates (dropdown selects)
        selects = page.locator("select")
        select_count = await selects.count()
        if select_count >= 2 and (start_month or start_year):
            if start_month:
                await _set_select_option(selects.nth(0), start_month)
            if start_year:
                await _set_select_option(selects.nth(1), start_year)

        if select_count >= 4 and (end_month or end_year):
            if end_month:
                await _set_select_option(selects.nth(2), end_month)
            if end_year:
                await _set_select_option(selects.nth(3), end_year)

        # Grade
        if grade:
            grade_input = page.locator("div:has(label:has-text('Grade')) input, input[id*='grade']").first
            if await grade_input.count() > 0:
                await grade_input.fill(grade)

        # Activities
        if activities:
            act_input = page.locator("div:has(label:has-text('Activities')) textarea, textarea[placeholder*='Alpha Phi Omega']").first
            if await act_input.count() > 0:
                await act_input.fill(activities)

        # Description
        if description:
            desc_input = page.locator("div:has(label:has-text('Description')) textarea, textarea[id*='description']").first
            if await desc_input.count() > 0:
                await desc_input.fill(description)

        # Click Save
        save_btn = page.locator("button:has-text('Save'), button.artdeco-button--primary").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate Save button on education form."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "message": f"Successfully added education at {school} to your profile.",
            "school": school,
            "degree": degree,
            "field_of_study": field_of_study
        }


@require_auth
async def add_experience(
    title: str,
    company: str,
    employment_type: Optional[str] = "",
    location: Optional[str] = "",
    location_type: Optional[str] = "",
    is_current: bool = True,
    start_month: Optional[str] = "",
    start_year: Optional[str] = "",
    end_month: Optional[str] = "",
    end_year: Optional[str] = "",
    description: Optional[str] = "",
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Add a work position or experience to your own LinkedIn profile.

    Security & Boundary Notice: Strictly locked to your authenticated account.

    Args:
        title: Job title (e.g. 'Full-Stack AI Engineer').
        company: Company or organization name (e.g. 'AltSchool Africa').
        employment_type: 'Full-time', 'Part-time', 'Contract', 'Internship', 'Freelance'.
        location: City or region (e.g. 'Lagos, Nigeria').
        location_type: 'On-site', 'Hybrid', or 'Remote'.
        is_current: Whether you currently work in this role (default: True).
        start_month: Start month (e.g. 'January').
        start_year: Start year (e.g. '2024').
        end_month: End month (if not current).
        end_year: End year (if not current).
        description: Role accomplishments and responsibilities.

    Returns:
        Status result indicating whether experience was added.
    """
    if not title or not title.strip():
        return {"success": False, "error": "EMPTY_TITLE", "message": "Job title is required."}
    if not company or not company.strip():
        return {"success": False, "error": "EMPTY_COMPANY", "message": "Company name is required."}

    async with browser_manager.get_page(headless=True) as page:
        opened = await _open_add_section_item(page, "Core", "Add position")
        if not opened:
            return {
                "success": False,
                "error": "MODAL_NOT_OPENED",
                "message": "Could not open the Add Position form from profile."
            }

        # Title
        title_input = page.locator("div:has(label:has-text('Title')) input, input[placeholder*='Senior Product Manager']").first
        if await title_input.count() > 0:
            await _fill_typeahead(page, title_input, title)

        # Employment type
        if employment_type:
            emp_sel = page.locator("div:has(label:has-text('Employment type')) select, select[id*='employmentType']").first
            if await emp_sel.count() > 0:
                await _set_select_option(emp_sel, employment_type)

        # Company
        comp_input = page.locator("div:has(label:has-text('Company')) input, input[placeholder*='Microsoft']").first
        if await comp_input.count() > 0:
            await _fill_typeahead(page, comp_input, company)

        # Location
        if location:
            loc_input = page.locator("div:has(label:has-text('Location')) input, input[placeholder*='City or region']").first
            if await loc_input.count() > 0:
                await _fill_typeahead(page, loc_input, location)

        # Location type
        if location_type:
            loctype_sel = page.locator("div:has(label:has-text('Location type')) select, select[id*='locationType']").first
            if await loctype_sel.count() > 0:
                await _set_select_option(loctype_sel, location_type)

        # Handle current role checkbox
        if not is_current:
            chk = page.locator("input[type='checkbox']").first
            if await chk.count() > 0 and await chk.is_checked():
                await chk.click()
                await human_delay(0.5, 1.0)

        # Dates
        selects = page.locator("select")
        select_count = await selects.count()
        # Find start month & year selects
        if start_month or start_year:
            m_sel = page.locator("div:has(label:has-text('Start month')) select, select[id*='startMonth']").first
            y_sel = page.locator("div:has(label:has-text('Start year')) select, select[id*='startYear']").first
            if await m_sel.count() > 0 and start_month:
                await _set_select_option(m_sel, start_month)
            if await y_sel.count() > 0 and start_year:
                await _set_select_option(y_sel, start_year)

        if not is_current and (end_month or end_year):
            em_sel = page.locator("div:has(label:has-text('End month')) select, select[id*='endMonth']").first
            ey_sel = page.locator("div:has(label:has-text('End year')) select, select[id*='endYear']").first
            if await em_sel.count() > 0 and end_month:
                await _set_select_option(em_sel, end_month)
            if await ey_sel.count() > 0 and end_year:
                await _set_select_option(ey_sel, end_year)

        # Description
        if description:
            desc_editor = page.locator("div[role='textbox'][contenteditable='true'], div:has(label:has-text('Description')) textarea").first
            if await desc_editor.count() > 0:
                await desc_editor.click()
                is_ce = await desc_editor.get_attribute("contenteditable") == "true"
                if is_ce:
                    await page.keyboard.insert_text(description)
                else:
                    await desc_editor.fill(description)
                await human_delay(0.5, 1.0)

        # Save
        save_btn = page.locator("button:has-text('Save'), button.artdeco-button--primary").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate Save button on position form."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "message": f"Successfully added position '{title}' at {company} to your profile.",
            "title": title,
            "company": company
        }


@require_auth
async def add_skill(skill_name: str, account_identity: AccountIdentity = None) -> Dict[str, Any]:
    """Add a skill to your own LinkedIn profile.

    Security & Boundary Notice: Strictly locked to your authenticated account.

    Args:
        skill_name: The name of the skill (e.g. 'Model Context Protocol (MCP)', 'Python', 'FastAPI').

    Returns:
        Status result indicating whether the skill was added.
    """
    if not skill_name or not skill_name.strip():
        return {"success": False, "error": "EMPTY_SKILL", "message": "Skill name cannot be empty."}

    skill_name = skill_name.strip()

    async with browser_manager.get_page(headless=True) as page:
        opened = await _open_add_section_item(page, "Core", "Add skills")
        if not opened:
            return {
                "success": False,
                "error": "MODAL_NOT_OPENED",
                "message": "Could not open the Add Skills form from profile."
            }

        # Locate skill input
        skill_input = page.locator("input[placeholder*='Skill (ex:'], input[id*='skill'], div:has(label:has-text('Skill')) input").first
        if await skill_input.count() == 0:
            return {
                "success": False,
                "error": "INPUT_NOT_FOUND",
                "message": "Could not find the Skill input field."
            }

        await skill_input.click()
        await skill_input.type(skill_name, delay=25)
        await human_delay(1.2, 2.0)

        # Pick suggestion or press Enter
        suggestion = page.locator("div[role='listbox'] div[role='option'], div.basic-typeahead__selectable-list li").first
        if await suggestion.count() > 0 and await suggestion.is_visible():
            await suggestion.click()
        else:
            await page.keyboard.press("Enter")
        await human_delay(1.0, 1.8)

        # Click Save
        save_btn = page.locator("button:has-text('Save'), button.artdeco-button--primary").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate Save button on skill modal."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "message": f"Successfully added skill '{skill_name}' to your profile.",
            "skill": skill_name
        }


@require_auth
async def add_project(
    title: str,
    description: Optional[str] = "",
    url: Optional[str] = "",
    start_month: Optional[str] = "",
    start_year: Optional[str] = "",
    end_month: Optional[str] = "",
    end_year: Optional[str] = "",
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Add a project to your own LinkedIn profile under Projects.

    Security & Boundary Notice: Strictly locked to your authenticated account.

    Args:
        title: Project title or name (e.g. 'Argus Agent', 'NairaPulse AI').
        description: Description of the project, architecture, tech stack, and achievements.
        url: Link to project demo or repository (appended to description if field not separate).
        start_month: Starting month (e.g. 'January').
        start_year: Starting year (e.g. '2024').
        end_month: Ending month (optional).
        end_year: Ending year (optional).

    Returns:
        Status result indicating whether the project was added.
    """
    if not title or not title.strip():
        return {"success": False, "error": "EMPTY_TITLE", "message": "Project title is required."}

    full_description = description or ""
    if url and url not in full_description:
        full_description = f"{full_description}\n\nProject Link: {url}".strip()

    async with browser_manager.get_page(headless=True) as page:
        opened = await _open_add_section_item(page, "Recommended", "Add projects")
        if not opened:
            return {
                "success": False,
                "error": "MODAL_NOT_OPENED",
                "message": "Could not open the Add Projects form from profile."
            }

        # Project name
        name_input = page.locator("div:has(label:has-text('Project name')) input, input[id*='name']").first
        if await name_input.count() > 0:
            await name_input.click()
            await name_input.type(title, delay=25)
            await human_delay(0.5, 1.0)

        # Description
        if full_description:
            desc_input = page.locator("div:has(label:has-text('Description')) textarea, textarea").first
            if await desc_input.count() > 0:
                await desc_input.click()
                await desc_input.fill(full_description)
                await human_delay(0.5, 1.0)

        # Dates
        selects = page.locator("select")
        select_count = await selects.count()
        if select_count >= 2 and (start_month or start_year):
            if start_month:
                await _set_select_option(selects.nth(0), start_month)
            if start_year:
                await _set_select_option(selects.nth(1), start_year)
        if select_count >= 4 and (end_month or end_year):
            if end_month:
                await _set_select_option(selects.nth(2), end_month)
            if end_year:
                await _set_select_option(selects.nth(3), end_year)

        # Save
        save_btn = page.locator("button:has-text('Save'), button.artdeco-button--primary").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate Save button on project form."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "message": f"Successfully added project '{title}' to your profile.",
            "title": title
        }


@require_auth
async def update_job_preferences(
    job_titles: Optional[List[str]] = None,
    location_types: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    employment_types: Optional[List[str]] = None,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Configure your 'Open to work' job preferences on LinkedIn.

    Security & Boundary Notice: Strictly locked to your authenticated account.

    Args:
        job_titles: List of target job titles (e.g. ['AI Engineer', 'Full-Stack Developer']).
        location_types: Workplace modes: ['On-site', 'Hybrid', 'Remote'].
        locations: Target cities or countries (e.g. ['Nigeria', 'United Kingdom']).
        employment_types: Types of work: ['Full-time', 'Part-time', 'Contract', 'Internship'].

    Returns:
        Status result indicating whether job preferences were updated.
    """
    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.my_profile_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Click Open to button
        open_to_btn = page.locator("button:has-text('Open to'), a:has-text('Open to')").first
        if await open_to_btn.count() == 0:
            return {
                "success": False,
                "error": "OPEN_TO_NOT_FOUND",
                "message": "Could not find the 'Open to' button on your profile."
            }

        await open_to_btn.evaluate("el => el.click()")
        await human_delay(1.5, 2.5)

        # Click 'Finding a new job'
        opened = await page.evaluate("""() => {
            const el = Array.from(document.querySelectorAll('div, li, a, button'))
                .find(e => e.innerText && e.innerText.includes('Finding a new job'));
            if (el) {
                el.click();
                return true;
            }
            return false;
        }""")
        if not opened:
            return {
                "success": False,
                "error": "OPTION_NOT_FOUND",
                "message": "Could not select 'Finding a new job' option."
            }

        await human_delay(2.0, 3.5)

        # 1. Job titles
        if job_titles:
            for jt in job_titles:
                add_title_btn = page.locator("button:has-text('Add title')").first
                if await add_title_btn.count() > 0:
                    await add_title_btn.click()
                    await human_delay(0.8, 1.5)
                    title_input = page.locator("div[role='dialog'] input, dialog input").last
                    if await title_input.count() > 0:
                        await _fill_typeahead(page, title_input, jt)

        # 2. Location types (pills: On-site, Hybrid, Remote)
        if location_types:
            for lt in ["On-site", "Hybrid", "Remote"]:
                pill = page.locator(f"button:has-text('{lt}')").first
                if await pill.count() > 0:
                    is_selected = await pill.evaluate("el => el.innerText.includes('✓') || el.classList.contains('artdeco-pill--selected') || el.getAttribute('aria-pressed') === 'true'")
                    should_be_selected = any(lt.lower() in t.lower() for t in location_types)
                    if is_selected != should_be_selected:
                        await pill.click()
                        await human_delay(0.4, 0.8)

        # 3. Locations
        if locations:
            for loc in locations:
                add_loc_btn = page.locator("button:has-text('Add location')").first
                if await add_loc_btn.count() > 0:
                    await add_loc_btn.click()
                    await human_delay(0.8, 1.5)
                    loc_input = page.locator("div[role='dialog'] input, dialog input").last
                    if await loc_input.count() > 0:
                        await _fill_typeahead(page, loc_input, loc)

        # 4. Employment types (pills: Full-time, Part-time, Contract, Internship)
        if employment_types:
            for et in ["Full-time", "Part-time", "Contract", "Internship"]:
                pill = page.locator(f"button:has-text('{et}')").first
                if await pill.count() > 0:
                    is_selected = await pill.evaluate("el => el.innerText.includes('✓') || el.classList.contains('artdeco-pill--selected') || el.getAttribute('aria-pressed') === 'true'")
                    should_be_selected = any(et.lower() in t.lower() for t in employment_types)
                    if is_selected != should_be_selected:
                        await pill.click()
                        await human_delay(0.4, 0.8)

        # Click Save & continue or Save
        save_btn = page.locator("button:has-text('Save & continue'), button:has-text('Save')").first
        if await save_btn.count() == 0:
            return {
                "success": False,
                "error": "SAVE_BUTTON_NOT_FOUND",
                "message": "Could not locate Save button on preferences form."
            }

        await save_btn.click()
        await human_delay(2.5, 4.0)

        return {
            "success": True,
            "boundary": "AUTHENTICATED_SELF_ONLY",
            "message": "Successfully configured your job preferences.",
            "location_types": location_types,
            "employment_types": employment_types
        }

