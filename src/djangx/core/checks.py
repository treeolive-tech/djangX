# ramani: src/djangx/core/checks.py
"""System checks for djangX configuration."""

from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.checks import CheckMessage, Error, register

from ..contrib.sass.apps import SassConfig
from .apps import CoreConfig

SETTING_APP_REQUIREMENTS: dict[str, str] = {
    "BOOTSTRAP_INCLUDES": SassConfig.name,
    "SASS_DART_OPTIONS": SassConfig.name,
    "SASS_EXECUTABLE": SassConfig.name,
    "SASS_GITIGNORE": SassConfig.name,
}


@register("settings")
def configured_settings_have_required_apps(**kwargs: Any) -> list[CheckMessage]:
    """Ensure apps required by configured settings are installed."""
    missing_apps: dict[str, list[str]] = {}
    for setting_name, app_name in SETTING_APP_REQUIREMENTS.items():
        if getattr(settings, setting_name, None) is not None and not apps.is_installed(
            app_name
        ):
            missing_apps.setdefault(app_name, []).append(setting_name)

    if not missing_apps:
        return []

    details = "; ".join(
        f"'{app_name}' ({', '.join(sorted(setting_names))})"
        for app_name, setting_names in sorted(missing_apps.items())
    )
    app_names = ", ".join(repr(app_name) for app_name in sorted(missing_apps))
    return [
        Error(
            f"Configured settings require apps missing from INSTALLED_APPS: {details}.",
            hint=f"Add {app_names} to INSTALLED_APPS.",
            id=f"{CoreConfig.name}.E001",
        )
    ]
