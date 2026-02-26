"""Tests for API app."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Organisation, Site, User, BudgetCategory
from expenses.models import Expense


class APIAuthTest(TestCase):
    """API requires authentication."""

    def setUp(self):
        self.client = APIClient()

    def test_sites_require_auth(self):
        response = self.client.get("/api/v1/sites/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sites_with_token(self):
        org = Organisation.objects.create(name="Test", country="UK")
        site = Site.objects.create(organisation=org, name="Kampala", country="Uganda")
        user = User.objects.create_user(
            username="apiuser",
            password="testpass123",
            organisation=org,
            site=site,
            role="caretaker",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get("/api/v1/sites/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Kampala")


class SyncEndpointTest(TestCase):
    """Sync pull requires updated_after."""

    def setUp(self):
        self.client = APIClient()
        org = Organisation.objects.create(name="Test", country="UK")
        self.user = User.objects.create_user(
            username="syncuser",
            password="testpass123",
            organisation=org,
            role="caretaker",
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_sync_pull_requires_updated_after(self):
        response = self.client.get("/api/v1/sync/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("updated_after", response.data["detail"])
