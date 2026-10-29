from importlib import import_module
from importlib.util import find_spec

from django.apps import apps
from django.conf import settings
from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver

_used_home_url: bool = False


def _url_prefix(setting_name: str, default: str = "") -> str:
    """Return the `setting_name` URL prefix (or `default`) with a trailing slash, or `""` if empty.

    Examples::

        _url_prefix("ADMIN_URL", "admin")  # "admin/"
        _url_prefix("HOME_URL")  # ""
    """
    url = str(getattr(settings, setting_name, None) or default).strip("/")
    return f"{url}/" if url else ""


def home_url() -> str:
    """Return the `HOME_URL` prefix with a trailing slash, or `""` if unset.

    Examples::

        home_url()  # "start/"
    """
    global _used_home_url
    _used_home_url = True
    return _url_prefix("HOME_URL")


def home_url_was_used() -> bool:
    """Return whether `home_url()` has been called.

    Examples::

        home_url_was_used()  # False
    """
    return _used_home_url


def _app_urls() -> list[URLPattern | URLResolver]:
    """Include `<app>.urls` for every installed `app.*` config that defines `urlpatterns`.

    The app named by `settings.HOME_APP` is mounted at `home_url()` and placed last.

    Examples::

        _app_urls()  # [path("blog/", include("app.blog.urls")), path("", include("app.main.urls"))]
    """
    patterns: list[URLPattern | URLResolver] = []
    home: list[URLPattern | URLResolver] = []
    home_app: str = getattr(settings, "HOME_APP", None) or "app.main"

    for config in apps.get_app_configs():
        if not config.name.startswith("app."):
            continue
        module = f"{config.name}.urls"
        if not (find_spec(module) and hasattr(import_module(module), "urlpatterns")):
            continue
        if config.name == home_app:
            home.append(path(home_url(), include(module)))
        else:
            patterns.append(path(f"{config.label}/", include(module)))
    return [*patterns, *home]  # home may be a catch-all (""), so it goes last


# ----------------------------------------------------------

urlpatterns: list[URLPattern | URLResolver] = []

# ----------------------------------------------------------

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns.append(
        path(
            _url_prefix("RELOAD_URL", "__reload__"),
            include("django_browser_reload.urls"),
        )
    )
    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))

# ----------------------------------------------------------

if apps.is_installed("django.contrib.admin"):
    from django.contrib import admin

    urlpatterns.append(path(_url_prefix("ADMIN_URL", "admin"), admin.site.urls))

# ----------------------------------------------------------

urlpatterns.extend(
    [
        path(
            _url_prefix("REST_AUTH_URL", "__api-auth__"),
            include("rest_framework.urls"),
        ),
        *_app_urls(),
    ]
)
