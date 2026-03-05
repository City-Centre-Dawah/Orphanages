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

            _original_from_config = Flow.from_client_config.__func__

            @classmethod
            def _patched_from_config(cls, client_config, scopes, **kwargs):
                kwargs.setdefault("autogenerate_code_verifier", False)
                return _original_from_config(cls, client_config, scopes, **kwargs)

            Flow.from_client_config = _patched_from_config
        except (ImportError, AttributeError):
            pass
