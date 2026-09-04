"""Unit and boundary tests for LinkedIn MCP server using standard library unittest."""

import asyncio
import inspect
import unittest

from unittest.mock import patch
from linkedin_mcp.tools import self_profile, posts, messaging, browsing, network, auth, analytics, skills
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
            analytics.get_profile_views,
            skills.analyze_profile_strength,
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

    def test_unauthenticated_guardrail_blocks_poll(self):
        """Ensure that creating a poll without auth fails cleanly."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(posts.create_poll(question="Favorite AI model?", options=["Claude", "Gemini", "Grok"]))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_create_poll_validation(self):
        """Ensure poll requires at least 2 options and maximum 4."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session"):
            # Less than 2 options
            result = asyncio.run(posts.create_poll(question="Test?", options=["Only One"]))
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "INSUFFICIENT_OPTIONS")

            # More than 4 options
            result = asyncio.run(posts.create_poll(question="Test?", options=["1", "2", "3", "4", "5"]))
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "TOO_MANY_OPTIONS")

    def test_post_with_missing_media_file(self):
        """Ensure create_post rejects non-existent media paths immediately."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session"):
            result = asyncio.run(posts.create_post(text="Hello with image", media_path="non_existent_image_12345.png"))
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "MEDIA_NOT_FOUND")
            self.assertIn("does not exist", result["message"])

    def test_unauthenticated_guardrail_blocks_messaging(self):
        """Ensure that messaging without auth fails cleanly."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(messaging.send_message(
                recipient_profile_url="https://linkedin.com/in/test",
                message_text="Hi"
            ))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_unauthenticated_guardrail_blocks_get_conversation_messages(self):
        """Ensure reading conversation history without auth fails cleanly."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(messaging.get_conversation_messages(recipient_name="John Doe"))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_manage_invitation_validation(self):
        """Ensure manage_invitation validates action input."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session"):
            result = asyncio.run(network.manage_invitation(sender_name="Jane Doe", action="invalid_action"))
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "INVALID_ACTION")
            self.assertIn("Action must be either", result["message"])

    def test_unauthenticated_guardrail_blocks_analytics(self):
        """Ensure analytics tools fail cleanly when unauthenticated."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(analytics.get_post_analytics(limit=5))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

            result_views = asyncio.run(analytics.get_profile_views())
            self.assertFalse(result_views["success"])
            self.assertEqual(result_views["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_unauthenticated_guardrail_blocks_skills(self):
        """Ensure agentic skill tools fail cleanly when unauthenticated."""
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("Not logged in")):
            result = asyncio.run(skills.get_network_briefing(limit=3))
            self.assertFalse(result["success"])
            self.assertEqual(result["boundary_status"], "BLOCKED_UNAUTHENTICATED")

            result_strength = asyncio.run(skills.analyze_profile_strength())
            self.assertFalse(result_strength["success"])
            self.assertEqual(result_strength["boundary_status"], "BLOCKED_UNAUTHENTICATED")

    def test_session_health_sliding_window_telemetry(self):
        """Ensure get_session_health accurately reports session freshness and age."""
        import time
        from linkedin_mcp.auth.manager import auth_manager, AccountIdentity

        now = time.time()

        # Healthy session (<48h since refresh, <45d total age)
        mock_healthy = AccountIdentity(
            vanity_name="test-user",
            name="Test User",
            profile_url="https://linkedin.com/in/test-user",
            last_verified=now - 3600,
            first_authenticated=now - (10 * 86400),
            last_active_refresh=now - 3600,
        )
        with patch.object(auth_manager, "get_cached_identity", return_value=mock_healthy):
            health = auth_manager.get_session_health()
            self.assertEqual(health["status"], "HEALTHY")
            self.assertGreater(health["estimated_sliding_window_days_remaining"], 25)

        # Inactive session (>48h since refresh)
        mock_inactive = AccountIdentity(
            vanity_name="test-user",
            name="Test User",
            profile_url="https://linkedin.com/in/test-user",
            last_verified=now - (50 * 3600),
            first_authenticated=now - (10 * 86400),
            last_active_refresh=now - (50 * 3600),
        )
        with patch.object(auth_manager, "get_cached_identity", return_value=mock_inactive):
            health = auth_manager.get_session_health()
            self.assertEqual(health["status"], "NEEDS_REFRESH")

        # Stale session (>45d total age)
        mock_stale = AccountIdentity(
            vanity_name="test-user",
            name="Test User",
            profile_url="https://linkedin.com/in/test-user",
            last_verified=now - 3600,
            first_authenticated=now - (50 * 86400),
            last_active_refresh=now - 3600,
        )
        with patch.object(auth_manager, "get_cached_identity", return_value=mock_stale):
            health = auth_manager.get_session_health()
            self.assertEqual(health["status"], "STALE_REAUTH_RECOMMENDED")


if __name__ == "__main__":
    unittest.main()
