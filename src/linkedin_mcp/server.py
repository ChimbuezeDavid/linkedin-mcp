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
)
from linkedin_mcp.tools.self_profile import (
    get_my_profile as _get_my_profile,
    update_my_headline as _update_my_headline,
    update_my_about as _update_my_about,
)
from linkedin_mcp.tools.browsing import (
    search_people as _search_people,
    view_profile as _view_profile,
)
from linkedin_mcp.tools.posts import (
    create_post as _create_post,
    get_feed as _get_feed,
    comment_on_post as _comment_on_post,
)
from linkedin_mcp.tools.messaging import (
    list_conversations as _list_conversations,
    send_message as _send_message,
)
from linkedin_mcp.tools.network import (
    send_connection_request as _send_connection_request,
    get_pending_invitations as _get_pending_invitations,
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
async def create_post(text: str) -> Dict[str, Any]:
    """Publish a post to your LinkedIn feed authored exclusively by your profile.

    Args:
        text: The text content of your post.
    """
    return await _create_post(text=text)


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
