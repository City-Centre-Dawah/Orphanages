from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        import logging
        import core.signals  # noqa: F401
        self._patch_google_sso_pkce()
        logging.getLogger(__name__).warning("Google SSO PKCE patch loaded")

    @staticmethod
    def _patch_google_sso_pkce():
        """Disable PKCE in google-auth-oauthlib for django-google-sso compatibility.

        google-auth-oauthlib >= 1.0 enables PKCE by default
        (autogenerate_code_verifier=True). django-google-sso creates a new
        Flow instance per request, so the code_verifier generated during
        start_login is lost by the time callback runs fetch_token.

        This patch passes autogenerate_code_verifier=False through
        Flow.from_client_config (which pops it from kwargs at line 163 of
        flow.py and forwards it to the constructor). PKCE is optional for
        confidential server-side clients (RFC 7636).

        Defence-in-depth: requirements.txt also pins google-auth-oauthlib<1.0
        so fresh installs won't need this patch, but it protects existing
        environments where 1.x is already installed.
        """
        try:
            from google_auth_oauthlib.flow import Flow

            _original = Flow.from_client_config.__func__

            @classmethod
            def _patched(cls, client_config, scopes, **kwargs):
                kwargs.setdefault("autogenerate_code_verifier", False)
                return _original(cls, client_config, scopes, **kwargs)

            Flow.from_client_config = _patched
        except (ImportError, AttributeError):
            pass
