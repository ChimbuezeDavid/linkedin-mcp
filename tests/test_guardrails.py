"""Unit and boundary tests for LinkedIn MCP server using standard library unittest."""

import asyncio
import inspect
import unittest

from unittest.mock import patch
from linkedin_mcp.tools import self_profile, posts, messaging, browsing, network, auth
from linkedin_mcp.auth import session_guard


class TestLinkedInGuardrails(unittest.TestCase):

    def test_self_profile_tools_have_no_target_parameter(self):
        """Verify that self-profile mutation tools CANNOT accept a target profile URL."""
        profile_mutation_tools = [
            self_profile.update_my_headline,
            self_profile.update_my_about,
            self_profile.get_my_profile,
            self_profile.add_education,
            self_profile.add_experience,
            self_profile.add_skill,
            self_profile.add_project,
            self_profile.update_job_preferences,
            self_profile.update_my_services,
        ]
        for tool_fn in profile_mutation_tools:
            sig = inspect.signature(tool_fn)
            self.assertNotIn("profile_url", sig.parameters, f"{tool_fn.__name__} must not accept profile_url")
            self.assertNotIn("target", sig.parameters, f"{tool_fn.__name__} must not accept target")
            self.assertNotIn("target_profile_url", sig.parameters, f"{tool_fn.__name__} must not accept target_profile_url")

    def test_unauthenticated_guardrail_blocks_profile_edit(self):
        """Ensure that attempting to update a headline without auth fails cleanly."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(self_profile.update_my_headline(headline="Software Architect"))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")
            self.assertIn("linkedin_start_login", result["instruction"])

    def test_unauthenticated_guardrail_blocks_posting(self):
        """Ensure that attempting to post without auth fails cleanly."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(posts.create_post(text="Hello world"))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_unauthenticated_guardrail_blocks_messaging(self):
        """Ensure that messaging without auth fails cleanly."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(messaging.send_message(
                recipient_profile_url="https://linkedin.com/in/test",
                message_text="Hi"
            ))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
