"""LinkedIn MCP Server: Universal LinkedIn agent operating within the authenticated user's account."""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional
try:
    from mcp.server.mcpserver import MCPServer
    ServerClass = MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP
    ServerClass = FastMCP

from linkedin_mcp.tools.auth import (
    linkedin_login_status,
    linkedin_start_login,
    linkedin_logout,
    refresh_session as _refresh_session,
)
from linkedin_mcp.tools.self_profile import (
    get_my_profile as _get_my_profile,
    update_my_headline as _update_my_headline,
    update_my_about as _update_my_about,
    add_education as _add_education,
    add_experience as _add_experience,
    add_skill as _add_skill,
    add_project as _add_project,
    update_job_preferences as _update_job_preferences,
    update_my_services as _update_my_services,
)
from linkedin_mcp.tools.browsing import (
    search_people as _search_people,
    view_profile as _view_profile,
)
from linkedin_mcp.tools.posts import (
    create_post as _create_post,
    create_poll as _create_poll,
    get_feed as _get_feed,
    comment_on_post as _comment_on_post,
)
from linkedin_mcp.tools.analytics import (
    get_post_analytics as _get_post_analytics,
    get_profile_views as _get_profile_views,
)
from linkedin_mcp.tools.messaging import (
    list_conversations as _list_conversations,
    get_conversation_messages as _get_conversation_messages,
    send_message as _send_message,
)
from linkedin_mcp.tools.network import (
    send_connection_request as _send_connection_request,
    get_pending_invitations as _get_pending_invitations,
    manage_invitation as _manage_invitation,
)
from linkedin_mcp.tools.skills import (
    get_network_briefing as _get_network_briefing,
    analyze_profile_strength as _analyze_profile_strength,
)

# Configure logging to stderr (stdio is reserved for JSON-RPC MCP messages)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("linkedin_mcp")

from starlette.responses import HTMLResponse, JSONResponse

# Initialize MCP Server
mcp = ServerClass(
    name="LinkedIn MCP",
    instructions=(
        "Universal LinkedIn MCP Server operating strictly within the authenticated user's account boundary. "
        "Profile mutations are hard-locked to the authenticated user's own profile (/in/me). "
        "Searches, messages, connections, and posts are all authored and executed from the user's account."
    ),
)


@mcp.custom_route("/", methods=["GET", "HEAD"])
async def root_status(request):
    """Landing route indicating MCP server health and endpoint links."""
    return HTMLResponse(
        """<!DOCTYPE html>
<html>
<head><title>LinkedIn MCP Server</title></head>
<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
    <h2>LinkedIn MCP Server is Online</h2>
    <p>Status: Active and Ready</p>
    <p>For Grok Connectors, use the SSE URL: <strong>/sse</strong></p>
</body>
</html>"""
    )


# ==========================================
# Authentication & Session Tools
# ==========================================

@mcp.tool()
async def check_login_status() -> Dict[str, Any]:
    """Check LinkedIn authentication status and inspect the active user's identity details."""
    return await linkedin_login_status()


@mcp.tool()
async def start_login(timeout_seconds: int = 300) -> Dict[str, Any]:
    """Open an interactive browser window to sign in to LinkedIn, solve 2FA, and save the session.

    Args:
        timeout_seconds: Maximum time in seconds to wait for sign-in (default: 300).
    """
    return await linkedin_start_login(timeout_seconds=timeout_seconds)


@mcp.tool()
async def logout() -> Dict[str, Any]:
    """Clear all stored LinkedIn session credentials, cookies, and local profile caches."""
    return await linkedin_logout()


@mcp.tool()
async def refresh_session() -> Dict[str, Any]:
    """Test and extend the active LinkedIn session validity with sliding window keep-alive telemetry."""
    return await _refresh_session()


# ==========================================
# Self-Profile Management (Strictly User-Only)
# ==========================================

@mcp.tool()
async def get_my_profile() -> Dict[str, Any]:
    """Retrieve full profile details for your own authenticated LinkedIn profile.

    Security Notice: This tool can only read your own profile information.
    """
    return await _get_my_profile()


@mcp.tool()
async def update_my_headline(headline: str) -> Dict[str, Any]:
    """Update the headline on your own LinkedIn profile.

    Security Notice: Strictly locked to your authenticated account. Does not accept any other profile target.

    Args:
        headline: New headline text to display under your name.
    """
    return await _update_my_headline(headline=headline)


@mcp.tool()
async def update_my_about(summary: str) -> Dict[str, Any]:
    """Update the About / summary section on your own LinkedIn profile.

    Security Notice: Strictly locked to your authenticated account.

    Args:
        summary: New bio/summary text for your About section.
    """
    return await _update_my_about(summary=summary)


@mcp.tool()
async def add_education(
    school: str,
    degree: str = "",
    field_of_study: str = "",
    start_month: str = "",
    start_year: str = "",
    end_month: str = "",
    end_year: str = "",
    grade: str = "",
    activities: str = "",
    description: str = ""
) -> Dict[str, Any]:
    """Add an education credential to your own LinkedIn profile.

    Security Notice: Strictly locked to your authenticated account (/in/me).

    Args:
        school: Name of university or school (e.g. 'Afe Babalola University').
        degree: Degree type (e.g. 'Bachelor of Science - BSc').
        field_of_study: Major or area of study (e.g. 'Computer Science', 'Data Analysis').
        start_month: Starting month (e.g. 'September').
        start_year: Starting year (e.g. '2020').
        end_month: Graduation or ending month (e.g. 'June').
        end_year: Graduation or ending year (e.g. '2024').
        grade: GPA or honors (optional).
        activities: Clubs, societies, sports (optional).
        description: Notes, courses, or achievements (optional).
    """
    return await _add_education(
        school=school,
        degree=degree,
        field_of_study=field_of_study,
        start_month=start_month,
        start_year=start_year,
        end_month=end_month,
        end_year=end_year,
        grade=grade,
        activities=activities,
        description=description
    )


@mcp.tool()
async def add_experience(
    title: str,
    company: str,
    employment_type: str = "",
    location: str = "",
    location_type: str = "",
    is_current: bool = True,
    start_month: str = "",
    start_year: str = "",
    end_month: str = "",
    end_year: str = "",
    description: str = ""
) -> Dict[str, Any]:
    """Add a work position or experience to your own LinkedIn profile.

    Security Notice: Strictly locked to your authenticated account (/in/me).

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
    """
    return await _add_experience(
        title=title,
        company=company,
        employment_type=employment_type,
        location=location,
        location_type=location_type,
        is_current=is_current,
        start_month=start_month,
        start_year=start_year,
        end_month=end_month,
        end_year=end_year,
        description=description
    )


@mcp.tool()
async def add_skill(skill_name: str) -> Dict[str, Any]:
    """Add a skill to your own LinkedIn profile.

    Security Notice: Strictly locked to your authenticated account (/in/me).

    Args:
        skill_name: The name of the skill (e.g. 'Model Context Protocol (MCP)', 'Python', 'FastAPI').
    """
    return await _add_skill(skill_name=skill_name)


@mcp.tool()
async def add_project(
    title: str,
    description: str = "",
    url: str = "",
    start_month: str = "",
    start_year: str = "",
    end_month: str = "",
    end_year: str = ""
) -> Dict[str, Any]:
    """Add a project to your own LinkedIn profile under Projects.

    Security Notice: Strictly locked to your authenticated account (/in/me).

    Args:
        title: Project title or name (e.g. 'Argus Agent', 'NairaPulse AI').
        description: Description of the project, architecture, tech stack, and achievements.
        url: Link to project demo or repository (optional).
        start_month: Starting month (e.g. 'January').
        start_year: Starting year (e.g. '2024').
        end_month: Ending month (optional).
        end_year: Ending year (optional).
    """
    return await _add_project(
        title=title,
        description=description,
        url=url,
        start_month=start_month,
        start_year=start_year,
        end_month=end_month,
        end_year=end_year
    )


@mcp.tool()
async def update_job_preferences(
    job_titles: Optional[List[str]] = None,
    location_types: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    employment_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Configure your 'Open to work' job preferences on LinkedIn.

    Security Notice: Strictly locked to your authenticated account (/in/me).

    Args:
        job_titles: List of target job titles (e.g. ['AI Engineer', 'Full-Stack Developer']).
        location_types: Workplace modes: ['On-site', 'Hybrid', 'Remote'].
        locations: Target cities or countries (e.g. ['Nigeria', 'United Kingdom']).
        employment_types: Types of work: ['Full-time', 'Part-time', 'Contract', 'Internship'].
    """
    return await _update_job_preferences(
        job_titles=job_titles,
        location_types=location_types,
        locations=locations,
        employment_types=employment_types
    )


@mcp.tool()
async def update_my_services(
    services_to_add: Optional[List[str]] = None,
    services_to_remove: Optional[List[str]] = None,
    description: str = ""
) -> Dict[str, Any]:
    """Configure or update client services listed on your own LinkedIn profile.

    Security Notice: Strictly locked to your authenticated account (/in/me).

    Args:
        services_to_add: List of service names to add (e.g. ['Custom Software Development', 'Web Development']).
        services_to_remove: List of service names to remove (e.g. ['Graphic Design']).
        description: Summary of client offerings and experience (up to 500 characters).
    """
    return await _update_my_services(
        services_to_add=services_to_add,
        services_to_remove=services_to_remove,
        description=description
    )




# ==========================================
# Network, Browsing & Search
# ==========================================

@mcp.tool()
async def search_people(
    keywords: str,
    location: str = "",
    current_company: str = "",
    limit: int = 10
) -> Dict[str, Any]:
    """Search for professionals on LinkedIn through your authenticated account.

    Args:
        keywords: Search term (e.g. name, title, skills).
        location: Optional location filter (e.g. 'San Francisco', 'United Kingdom').
        current_company: Optional current company name.
        limit: Maximum results to retrieve (default: 10, max: 25).
    """
    return await _search_people(
        keywords=keywords,
        location=location,
        current_company=current_company,
        limit=limit
    )


@mcp.tool()
async def view_profile(profile_url: str) -> Dict[str, Any]:
    """View another LinkedIn member's profile as your authenticated user (strictly read-only).

    Args:
        profile_url: The member's profile URL or vanity username.
    """
    return await _view_profile(profile_url=profile_url)


# ==========================================
# Content & Feed
# ==========================================

@mcp.tool()
async def create_post(text: str, media_path: Optional[str] = None) -> Dict[str, Any]:
    """Publish a post to your LinkedIn feed authored exclusively by your profile, optionally attaching an image or document.

    Args:
        text: The text content of your post.
        media_path: Optional path to an image (.png, .jpg) or document (.pdf) to attach.
    """
    return await _create_post(text=text, media_path=media_path)


@mcp.tool()
async def create_poll(
    question: str,
    options: List[str],
    duration: str = "1_week"
) -> Dict[str, Any]:
    """Create and publish an interactive poll to your LinkedIn feed.

    Args:
        question: The question for the poll (up to 140 chars).
        options: List of poll answer options (minimum 2, maximum 4 options, each up to 30 chars).
        duration: Duration for the poll to run: '1_day', '3_days', '1_week', or '2_weeks' (default: '1_week').
    """
    return await _create_poll(question=question, options=options, duration=duration)


@mcp.tool()
async def get_feed(limit: int = 5) -> Dict[str, Any]:
    """Read recent posts from your personal LinkedIn home feed.

    Args:
        limit: Number of posts to read (default: 5, max: 15).
    """
    return await _get_feed(limit=limit)


@mcp.tool()
async def comment_on_post(post_url: str, comment_text: str) -> Dict[str, Any]:
    """Leave a comment on a LinkedIn post as your authenticated account.

    Args:
        post_url: The URL of the post.
        comment_text: The comment text to publish.
    """
    return await _comment_on_post(post_url=post_url, comment_text=comment_text)


# ==========================================
# Analytics & Insights
# ==========================================

@mcp.tool()
async def get_post_analytics(limit: int = 5) -> Dict[str, Any]:
    """Retrieve engagement metrics (impressions, reactions, comments, reposts) for recent posts authored by your account.

    Args:
        limit: Maximum number of recent posts to analyze (default: 5, max: 15).
    """
    return await _get_post_analytics(limit=limit)


@mcp.tool()
async def get_profile_views() -> Dict[str, Any]:
    """Retrieve private profile view analytics and viewer demographics for your account."""
    return await _get_profile_views()


# ==========================================
# Direct Messaging
# ==========================================

@mcp.tool()
async def list_conversations(limit: int = 10) -> Dict[str, Any]:
    """List recent direct message conversations from your authenticated inbox.

    Args:
        limit: Maximum conversations to retrieve (default: 10, max: 20).
    """
    return await _list_conversations(limit=limit)


@mcp.tool()
async def get_conversation_messages(recipient_name: str, limit: int = 10) -> Dict[str, Any]:
    """Read full message history and replies for a specific conversation in your inbox.

    Args:
        recipient_name: Name or keyword matching the conversation partner.
        limit: Maximum number of recent messages to retrieve (default: 10, max: 30).
    """
    return await _get_conversation_messages(recipient_name=recipient_name, limit=limit)


@mcp.tool()
async def send_message(recipient_profile_url: str, message_text: str) -> Dict[str, Any]:
    """Send a direct message to a LinkedIn member from your authenticated account.

    Args:
        recipient_profile_url: Profile URL of the recipient.
        message_text: The message body to send.
    """
    return await _send_message(
        recipient_profile_url=recipient_profile_url,
        message_text=message_text
    )


# ==========================================
# Network & Connections
# ==========================================

@mcp.tool()
async def send_connection_request(profile_url: str, custom_note: str = "") -> Dict[str, Any]:
    """Send a connection invitation to a professional from your authenticated account.

    Args:
        profile_url: Profile URL of the member to connect with.
        custom_note: Optional personalized message (up to 300 characters).
    """
    return await _send_connection_request(
        profile_url=profile_url,
        custom_note=custom_note
    )


@mcp.tool()
async def get_pending_invitations() -> Dict[str, Any]:
    """List pending incoming connection invitations received by your account."""
    return await _get_pending_invitations()


@mcp.tool()
async def manage_invitation(sender_name: str, action: str = "accept") -> Dict[str, Any]:
    """Accept or ignore a pending incoming connection invitation.

    Args:
        sender_name: Name of the person whose invitation to manage.
        action: Either 'accept' or 'ignore' (default: 'accept').
    """
    return await _manage_invitation(sender_name=sender_name, action=action)


# ==========================================
# Agentic Skills & Automation
# ==========================================

@mcp.tool()
async def get_network_briefing(limit: int = 5) -> Dict[str, Any]:
    """Synthesize a complete daily intelligence briefing: unread messages, pending invitations, post analytics, and top feed trends.

    Args:
        limit: Number of feed items and recent posts to include in the briefing (default: 5).
    """
    return await _get_network_briefing(limit=limit)


@mcp.tool()
async def analyze_profile_strength() -> Dict[str, Any]:
    """Audit your profile completeness, section strength, and generate actionable recommendations to optimize LinkedIn discoverability."""
    return await _analyze_profile_strength()


def main() -> None:
    """Run the LinkedIn MCP Server via stdio or SSE."""
    import argparse
    parser = argparse.ArgumentParser(description="LinkedIn MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn
        from starlette.middleware.cors import CORSMiddleware
        from mcp.server.transport_security import TransportSecuritySettings

        security_settings = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=["*"],
            allowed_origins=["*"],
        )

        if args.transport == "streamable-http":
            app = mcp.streamable_http_app(transport_security=security_settings)
        else:
            app = mcp.sse_app(transport_security=security_settings)

        # Allow browser clients (grok.com) to access without CORS restriction
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
