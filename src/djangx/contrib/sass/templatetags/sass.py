"""Template tags for linking the project's compiled Sass output."""

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import SafeString

from ..utils import SassBootstrap, SassStatic, SassWatcher

register = template.Library()

# CSS paths already compiled (if needed) and watched in this process.
_prepared: set[str] = set()


def _prepare(path: str) -> None:
    """In development, compile `path`'s source if stale and watch it for changes.

    Runs once per CSS path. Does nothing when `DEBUG` is off (production CSS is built
    by `djx collectstatic`) or when no matching source exists in an app's `static/`
    folder.
    """
    if not settings.DEBUG or path in _prepared:
        return
    found = SassStatic.source_for(path)
    if found is None:
        return
    source, folder = found
    output = source.with_suffix(".css")
    if not output.is_file() or output.stat().st_mtime < source.stat().st_mtime:
        SassWatcher.build()
    SassWatcher.watch(folder)
    _prepared.add(path)


@register.simple_tag
def bootstrap_css_url() -> str:
    """Return the static URL of the compiled Bootstrap CSS, or `""` if Bootstrap is off.

    Bootstrap is on when `BOOTSTRAP_INCLUDES` is not `None`. It is rebuilt by
    `runserver` when `BOOTSTRAP_INCLUDES` or `SASS_DART_OPTIONS` change.

    Examples::

        {% bootstrap_css_url %}  {# /static/vendor/bootstrap/css/compiled.css #}
    """
    if getattr(settings, "BOOTSTRAP_INCLUDES", None) is None:
        return ""
    return static(SassBootstrap.STATIC_PATH)


@register.simple_tag
def bootstrap_css() -> SafeString | str:
    """Return a `<link>` tag for the compiled Bootstrap CSS, or `""` if Bootstrap is off.

    Examples::

        {% load sass %}
        {% bootstrap_css %}  {# <link rel="stylesheet" href="/static/vendor/bootstrap/css/compiled.css"> #}
    """
    if not (url := bootstrap_css_url()):
        return ""
    return format_html('<link rel="stylesheet" href="{}">', url)


@register.simple_tag
def sass_url(path: str) -> str:
    """Return the static URL of one of your compiled CSS files.

    `path` mirrors the source file's location inside an app's `static/` folder, with
    a `.css` extension (`blog/css/site.scss` -> `blog/css/site.css`). The CSS is
    compiled next to its source. In development the first use also compiles the file
    if needed and starts watching its folder.

    Examples::

        {% sass_url "blog/css/site.css" %}  {# /static/blog/css/site.css #}
    """
    path = path.lstrip("/")
    _prepare(path)
    return static(path)


@register.simple_tag
def sass_css(path: str) -> SafeString:
    """Return a `<link>` tag for one of your compiled CSS files.

    Examples::

        {% load sass %}
        {% sass_css "blog/css/site.css" %}  {# <link rel="stylesheet" href="/static/blog/css/site.css"> #}
    """
    return format_html('<link rel="stylesheet" href="{}">', sass_url(path))
