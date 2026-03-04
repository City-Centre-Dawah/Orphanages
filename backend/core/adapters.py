"""
Social signup intercept: when allauth redirects to /accounts/social/signup/,
this view matches the Google email to an existing Django user, connects the
social account, logs them in, and redirects to /admin/.

No adapter hooks needed — works at the URL level.
"""

import logging

from allauth.socialaccount.internal.flows.signup import get_pending_signup
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login
from django.shortcuts import redirect

logger = logging.getLogger(__name__)
User = get_user_model()


def social_signup_intercept(request):
    """
    Replaces allauth's social signup view.
    Instead of showing a signup form, auto-connect to existing user by email.
    """
    sociallogin = get_pending_signup(request)
    if not sociallogin:
        messages.error(request, "No pending social login found. Please try again.")
        return redirect("/admin/login/")

    # Extract email from the social login
    email = ""
    if sociallogin.account.extra_data:
        email = sociallogin.account.extra_data.get("email", "")
    if not email:
        for addr in sociallogin.email_addresses:
            if hasattr(addr, "email"):
                email = addr.email
                break

    email = (email or "").lower().strip()
    logger.info("Social signup intercept: Google email = %s", email)

    if not email:
        messages.error(request, "No email returned from Google.")
        return redirect("/admin/login/")

    # Find existing user
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        messages.error(
            request,
            f"No account found for {email}. Ask an admin to create your account first.",
        )
        return redirect("/admin/login/")
    except User.MultipleObjectsReturned:
        user = User.objects.filter(email__iexact=email).first()

    # Link the social account to this user
    account = sociallogin.account
    account.user = user
    account.save()

    # Save token if present
    if sociallogin.token:
        sociallogin.token.account = account
        sociallogin.token.save()

    # Clear the pending signup from session
    request.session.pop("socialaccount_sociallogin", None)

    # Log them in
    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    logger.info("Social signup intercept: logged in user %s", user)
    return redirect("/admin/")
