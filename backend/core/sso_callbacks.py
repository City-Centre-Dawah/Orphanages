"""
Google SSO callbacks for auto-provisioning users.

Domain-based role assignment:
  @ccdawah.com             -> superuser + admin (UK leadership)
  @ccdawah.org             -> staff admin, "Admin" group (UK office)
  @orphanages.ccdawah.org  -> site_manager, "Site Manager" group (on-ground)
"""

import logging

from django.contrib.auth.models import Group
from django.http import HttpRequest

from core.models import Organisation

logger = logging.getLogger(__name__)

# Domain -> (role, is_staff, is_superuser, group_name or None)
DOMAIN_ROLE_MAP = {
    "ccdawah.com": ("admin", True, True, None),  # superuser bypasses all perms
    "ccdawah.org": ("admin", True, False, "Admin"),
    "orphanages.ccdawah.org": ("site_manager", True, False, "Site Manager"),
}


def pre_create_user(google_user_info: dict, request: HttpRequest) -> dict:
    """Called by django-google-sso before creating a new user.

    Returns extra fields to pass to User.objects.create().
    Sets role, is_staff, is_superuser, and organisation based on email domain.
    """
    email = google_user_info.get("email", "")
    domain = email.split("@")[-1].lower() if "@" in email else ""

    role, is_staff, is_superuser, _ = DOMAIN_ROLE_MAP.get(
        domain, ("viewer", False, False, None)
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

    Ensures domain-based role, staff status, and group assignment are correct.
    This runs on every SSO login so it self-heals if a user was created
    before seed_data was run, or if their flags were accidentally cleared.
    """
    email = user.email or ""
    domain = email.split("@")[-1].lower() if "@" in email else ""
    role, is_staff, is_superuser, group_name = DOMAIN_ROLE_MAP.get(
        domain, ("viewer", False, False, None)
    )

    # Ensure staff status and role match the domain policy
    changed_fields = []
    if not user.is_staff and is_staff:
        user.is_staff = True
        changed_fields.append("is_staff")
    if not user.is_superuser and is_superuser:
        user.is_superuser = True
        changed_fields.append("is_superuser")
    if user.role != role:
        user.role = role
        changed_fields.append("role")

    if changed_fields:
        user.save(update_fields=changed_fields)
        logger.info(
            "Updated SSO user %s: %s",
            email, ", ".join(f"{f}={getattr(user, f)}" for f in changed_fields),
        )

    # Assign permission group if not already a member
    if group_name and not user.groups.filter(name=group_name).exists():
        try:
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
            logger.info("Assigned group '%s' to user %s", group_name, email)
        except Group.DoesNotExist:
            logger.warning(
                "Group '%s' not found for user %s — run seed_data first",
                group_name, email,
            )
