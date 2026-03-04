"""
Custom allauth adapter: Google OAuth only works for existing Django users.

Matches Google email to an existing User. If no user with that email exists,
the login is rejected. This prevents random Google accounts from signing up.
"""

import logging

from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


class ExistingUserOnlySocialAdapter(DefaultSocialAccountAdapter):
    """Only allow Google login if a Django user with that email already exists."""

    def pre_social_login(self, request, sociallogin):
        """Auto-connect Google account to existing user by email match."""
        # If already connected to a user, nothing to do
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get("email", "").lower().strip()
        if not email:
            logger.warning("Google login attempt with no email")
            messages.error(request, "No email returned from Google.")
            raise ImmediateHttpResponse(redirect("/admin/login/"))

        # Try to find existing user by email
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            logger.warning("Google login rejected: no user with email %s", email)
            messages.error(
                request,
                f"No account found for {email}. Ask an admin to create your account first.",
            )
            raise ImmediateHttpResponse(redirect("/admin/login/"))

        # Connect the social account to the existing user
        sociallogin.connect(request, user)

        # Ensure allauth has an EmailAddress record too
        EmailAddress.objects.get_or_create(
            user=user,
            email=email,
            defaults={"verified": True, "primary": True},
        )

    def is_auto_signup_allowed(self, request, sociallogin):
        """Allow auto-signup only if we already connected in pre_social_login."""
        return sociallogin.is_existing
