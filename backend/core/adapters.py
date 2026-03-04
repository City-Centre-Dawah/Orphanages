"""
Custom allauth adapter: Google OAuth only works for existing Django users.

Matches Google email to an existing User. If no user with that email exists,
the login is rejected. This prevents random Google accounts from signing up.
"""

import logging

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


class ExistingUserOnlySocialAdapter(DefaultSocialAccountAdapter):
    """Only allow Google login if a Django user with that email already exists."""

    def pre_social_login(self, request, sociallogin):
        """Auto-connect Google account to existing user by email match."""
        logger.warning(">>> ADAPTER pre_social_login called, is_existing=%s", sociallogin.is_existing)

        # If already connected to a user, nothing to do
        if sociallogin.is_existing:
            return

        # Get email from Google
        email = ""
        if sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get("email", "")
        if not email:
            # Try from email_addresses list
            for addr in sociallogin.email_addresses:
                email = addr.email
                break

        email = email.lower().strip()
        logger.warning(">>> ADAPTER email from Google: '%s'", email)

        if not email:
            messages.error(request, "No email returned from Google.")
            raise ImmediateHttpResponse(redirect("/admin/login/"))

        # Try to find existing user by email
        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            logger.warning(">>> ADAPTER no user with email %s", email)
            messages.error(
                request,
                f"No account found for {email}. Ask an admin to create your account first.",
            )
            raise ImmediateHttpResponse(redirect("/admin/login/"))
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email__iexact=email).first()

        logger.warning(">>> ADAPTER matched user: %s (pk=%s)", user, user.pk)

        # Save the social account link
        sociallogin.user = user
        sociallogin.account.user = user
        sociallogin.account.save()
        if sociallogin.token:
            sociallogin.token.account = sociallogin.account
            sociallogin.token.save()

        # Log the user in directly and redirect to admin
        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.warning(">>> ADAPTER logged in user, redirecting to /admin/")
        raise ImmediateHttpResponse(redirect("/admin/"))

    def is_auto_signup_allowed(self, request, sociallogin):
        """Never allow signup — only existing users via pre_social_login."""
        return False

    def is_open_for_signup(self, request, sociallogin):
        """Block the signup form entirely."""
        return False
