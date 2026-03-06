"""
Google SSO callbacks for auto-provisioning users.

Domain-based role assignment:
  @ccdawah.com             -> superuser + admin (UK leadership)
  @ccdawah.org             -> staff admin (UK office)
  @orphanages.ccdawah.org  -> site_manager, admin access (on-ground site managers)
"""

import logging

from django.http import HttpRequest

from core.models import Organisation

logger = logging.getLogger(__name__)

# Domain -> (role, is_staff, is_superuser)
DOMAIN_ROLE_MAP = {
    "ccdawah.com": ("admin", True, True),
    "ccdawah.org": ("admin", True, False),
    "orphanages.ccdawah.org": ("site_manager", True, False),
}


def pre_create_user(google_user_info: dict, request: HttpRequest) -> dict:
    """Called by django-google-sso before creating a new user.

    Returns extra fields to pass to User.objects.create().
    Sets role, is_staff, is_superuser, and organisation based on email domain.
    """
    email = google_user_info.get("email", "")
    domain = email.split("@")[-1].lower() if "@" in email else ""

    role, is_staff, is_superuser = DOMAIN_ROLE_MAP.get(
        domain, ("viewer", False, False)
    )

    defaults = {
        "role": role,
        "is_staff": is_staff,
        "is_superuser": is_superuser,
    }

    # Assign the CCD organisation (there's only one)
    org = Organisation.objects.first()
    if org:
        defaults["organisation"] = org

    logger.info(
        "Auto-provisioning user %s: domain=%s, role=%s, is_staff=%s",
        email, domain, role, is_staff,
    )

    return defaults


def pre_login_user(user, request: HttpRequest) -> None:
    """Called by django-google-sso after user is retrieved but before login.

    No-op for now. Manual role changes are preserved (we don't override on login).
    """
