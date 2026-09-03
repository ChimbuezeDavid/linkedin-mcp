"""Unit and boundary tests for LinkedIn MCP server using standard library unittest."""

import asyncio
import inspect
import unittest

from linkedin_mcp.tools import self_profile, posts, messaging, browsing, network, auth


class TestLinkedInGuardrails(unittest.TestCase):

    def test_self_profile_tools_have_no_target_parameter(self):
        """Verify that self-profile mutation tools CANNOT accept a target profile URL."""
        headline_sig = inspect.signature(self_profile.update_my_headline)
        self.assertNotIn("profile_url", headline_sig.parameters)
        self.assertNotIn("target", headline_sig.parameters)
        self.assertIn("headline", headline_sig.parameters)

        about_sig = inspect.signature(self_profile.update_my_about)
        self.assertNotIn("profile_url", about_sig.parameters)
        self.assertNotIn("target", about_sig.parameters)
        self.assertIn("summary", about_sig.parameters)

        my_profile_sig = inspect.signature(self_profile.get_my_profile)
        self.assertNotIn("profile_url", my_profile_sig.parameters)

    def test_unauthenticated_guardrail_blocks_profile_edit(self):
        """Ensure that attempting to update a headline without auth fails cleanly."""
        auth.auth_manager.logout()

        result = asyncio.run(self_profile.update_my_headline(headline="Software Architect"))
        self.assertFalse(result["success"])
        self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")
        self.assertIn("linkedin_start_login", result["instruction"])

    def test_unauthenticated_guardrail_blocks_posting(self):
        """Ensure that attempting to post without auth fails cleanly."""
        auth.auth_manager.logout()

        result = asyncio.run(posts.create_post(text="Hello world"))
        self.assertFalse(result["success"])
        self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_unauthenticated_guardrail_blocks_messaging(self):
        """Ensure that messaging without auth fails cleanly."""
        auth.auth_manager.logout()

        result = asyncio.run(messaging.send_message(
            recipient_profile_url="https://linkedin.com/in/test",
            message_text="Hi"
        ))
        self.assertFalse(result["success"])
        self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_login_status_reports_unauthenticated(self):
        """Verify check_login_status reports UNAUTHENTICATED when logged out."""
        auth.auth_manager.logout()

        status = asyncio.run(auth.linkedin_login_status())
        self.assertFalse(status["is_authenticated"])
        self.assertEqual(status["status"], "UNAUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
