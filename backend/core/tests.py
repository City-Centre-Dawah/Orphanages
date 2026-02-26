"""Tests for core app."""

from django.test import Client, TestCase

from core.models import Organisation, Site, User


class HealthCheckTest(TestCase):
    """Health endpoint returns 200 when DB is reachable."""

    def test_health_returns_ok(self):
        client = Client()
        response = client.get("/health/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "connected")


class OrganisationModelTest(TestCase):
    """Organisation model creates and represents correctly."""

    def test_str(self):
        org = Organisation.objects.create(name="Test Org", country="UK", city="London")
        self.assertEqual(str(org), "Test Org")


class SiteModelTest(TestCase):
    """Site model requires organisation."""

    def test_site_belongs_to_org(self):
        org = Organisation.objects.create(name="Test", country="UK")
        site = Site.objects.create(organisation=org, name="Kampala", country="Uganda")
        self.assertEqual(site.organisation, org)
        self.assertIn("Kampala", str(site))


class UserModelTest(TestCase):
    """User extends AbstractUser with org, site, role."""

    def test_user_has_role(self):
        org = Organisation.objects.create(name="Test", country="UK")
        user = User.objects.create_user(
            username="caretaker1",
            password="testpass123",
            organisation=org,
            role="caretaker",
        )
        self.assertEqual(user.role, "caretaker")
