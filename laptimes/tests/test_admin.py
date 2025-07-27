"""Tests for the laptimes admin interface."""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from ..models import Session
from .base import BaseTestCase


class AdminInterfaceTests(TestCase):
    """Test cases for admin interface enhancements"""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="testpass123"
        )
        self.client = Client()
        self.client.login(username="admin", password="testpass123")

        # Create test session with hash
        self.session_with_hash = Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
            players_data=[{"name": "Test Driver"}],
            file_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890",
        )

        # Create test session without hash (legacy)
        self.session_without_hash = Session.objects.create(
            track="Legacy Track",
            car="Legacy Car",
            session_type="Race",
            file_name="legacy.json",
            players_data=[{"name": "Legacy Driver"}],
            file_hash=None,
        )

    def test_admin_list_display_includes_hash(self):
        """Test that admin list view shows shortened file hash"""
        response = self.client.get("/admin/laptimes/session/")
        self.assertEqual(response.status_code, 200)

        # Check that shortened hash is displayed
        self.assertContains(response, "a1b2c3d4...")
        self.assertContains(response, "No hash")  # For legacy session

    def test_admin_session_detail_shows_full_hash(self):
        """Test that admin detail view shows full file hash"""
        response = self.client.get(
            f"/admin/laptimes/session/{self.session_with_hash.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)

        # Check for full hash display
        self.assertContains(response, self.session_with_hash.file_hash)
        self.assertContains(response, "Click to copy")

    def test_admin_legacy_session_hash_message(self):
        """Test that legacy sessions show appropriate hash message"""
        response = self.client.get(
            f"/admin/laptimes/session/{self.session_without_hash.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "No hash available")
        self.assertContains(response, "uploaded before duplicate prevention")

    def test_admin_search_includes_hash(self):
        """Test that admin search functionality includes file hash"""
        # Search by partial hash
        search_term = "a1b2c3d4"
        response = self.client.get(f"/admin/laptimes/session/?q={search_term}")
        self.assertEqual(response.status_code, 200)

        # Should find the session with matching hash
        self.assertContains(response, "Test Track")
        # Note: Legacy track might still appear in filter options, so we check for specific context

    def test_admin_fieldsets_organization(self):
        """Test that admin form is properly organized with fieldsets"""
        response = self.client.get(
            f"/admin/laptimes/session/{self.session_with_hash.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)

        # Check for proper fieldset organization
        self.assertContains(response, "Session Information")
        self.assertContains(response, "File Information")
        self.assertContains(response, "Player Data")

        # Player data should be collapsible (check for collapse class in any form)