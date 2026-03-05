from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        import core.signals  # noqa: F401
        self._patch_google_sso_pkce()

    @staticmethod
    def _patch_google_sso_pkce():
        """Disable PKCE auto-generation in django-google-sso.

        google-auth-oauthlib >= 1.2 defaults to autogenerate_code_verifier=True,
        but django-google-sso doesn't persist the code_verifier between the
        start_login and callback views, causing "Missing code verifier" errors.
        This patch disables auto-generation until the library adds PKCE support.
        """
        try:
            from google_auth_oauthlib.flow import Flow

            _original_init = Flow.__init__

            def _patched_init(self, *args, **kwargs):
                kwargs.setdefault("autogenerate_code_verifier", False)
                _original_init(self, *args, **kwargs)

            Flow.__init__ = _patched_init
        except ImportError:
            pass
