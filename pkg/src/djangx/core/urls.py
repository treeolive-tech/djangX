from importlib import import_module
from importlib.util import find_spec

from django.apps import apps
from django.conf import settings
from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver

from .utils import Settings


def _app_urls() -> list[URLPattern | URLResolver]:
    """Include `<app>.urls` for every installed `app.*` config that defines `urlpatterns`.

    The app named by `settings.HOME_APP` is mounted at `Settings.home_url()` and placed last.

    Examples::

        _app_urls()  # [path("blog/", include("app.blog.urls")), path("", include("app.main.urls"))]
    """
    patterns: list[URLPattern | URLResolver] = []
    home: list[URLPattern | URLResolver] = []
    home_app: str | None = getattr(settings, "HOME_APP", None)

    for config in apps.get_app_configs():
        if not config.name.startswith("app."):
            continue
        module = f"{config.name}.urls"
        if not (find_spec(module) and hasattr(import_module(module), "urlpatterns")):
            continue
        if config.name == home_app:
            home.append(path(Settings.home_url(), include(module)))
        else:
            patterns.append(path(f"{config.label}/", include(module)))
    return [*patterns, *home]  # home may be a catch-all (""), so it goes last


# ----------------------------------------------------------

urlpatterns: list[URLPattern | URLResolver] = []

# ----------------------------------------------------------

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns.append(
        path(Settings.reload_url(), include("django_browser_reload.urls"))
    )
    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))

# ----------------------------------------------------------

if apps.is_installed("django.contrib.admin"):
    from django.contrib import admin

    urlpatterns.append(path(Settings.admin_url(), admin.site.urls))

# ----------------------------------------------------------

urlpatterns.extend(
    [
        path(Settings.rest_auth_url(), include("rest_framework.urls")),
        *_app_urls(),
    ]
)
