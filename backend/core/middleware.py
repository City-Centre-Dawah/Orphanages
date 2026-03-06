"""Diagnostic middleware for SSO troubleshooting.

TODO: Remove this module once Google SSO login is confirmed working.
"""

import logging

logger = logging.getLogger("core.sso_debug")


class SSODebugMiddleware:
    """Log request details for Google SSO callback to diagnose auth failures."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/google_sso/"):
            logger.warning(
                "SSO request | path=%s | method=%s | scheme=%s | host=%s | "
                "session_key=%s | GET=%s | X-Forwarded-Proto=%s",
                request.path,
                request.method,
                request.scheme,
                request.get_host(),
                request.session.session_key,
                dict(request.GET),
                request.META.get("HTTP_X_FORWARDED_PROTO", "(not set)"),
            )

        response = self.get_response(request)

        if request.path.startswith("/google_sso/"):
            logger.warning(
                "SSO response | path=%s | status=%s | location=%s",
                request.path,
                response.status_code,
                response.get("Location", "(none)"),
            )

        return response
