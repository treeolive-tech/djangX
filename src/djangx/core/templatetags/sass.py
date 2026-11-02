"""Template tags for linking the project's compiled Sass output."""

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import SafeString

from ..utils.sass import Sass

register = template.Library()


@register.simple_tag
def bootstrap_css_url() -> str:
    """Return the static URL of the compiled Bootstrap CSS, or `""` if Bootstrap is off.

    Bootstrap is on when `BOOTSTRAP_INCLUDES` is not `None`.

    Examples::

        {% bootstrap_css_url %}  {# /static/compiled_sass/bootstrap/output.css #}
    """
    if getattr(settings, "BOOTSTRAP_INCLUDES", None) is None:
        return ""
    return static(
        f"{Sass.OUTPUT_DIR}/{Sass.BOOTSTRAP_OUTPUT_DIR}/{Sass.CSS_OUTPUT_FILE}"
    )


@register.simple_tag
def bootstrap_css() -> SafeString | str:
    """Return a `<link>` tag for the compiled Bootstrap CSS, or `""` if Bootstrap is off.

    Examples::

        {% load sass %}
        {% bootstrap_css %}  {# <link rel="stylesheet" href="/static/compiled_sass/bootstrap/output.css"> #}
    """
    if not (url := bootstrap_css_url()):
        return ""
    return format_html('<link rel="stylesheet" href="{}">', url)


@register.simple_tag
def sass_url(path: str) -> str:
    """Return the static URL of one of your compiled CSS files.

    `path` mirrors the source file's location inside its `static/` folder, with a
    `.css` extension (`blog/css/site.scss` -> `blog/css/site.css`).

    Examples::

        {% sass_url "blog/css/site.css" %}  {# /static/compiled_sass/scss/blog/css/site.css #}
    """
    return static(f"{Sass.OUTPUT_DIR}/{Sass.SCSS_OUTPUT_DIR}/{path.lstrip('/')}")


@register.simple_tag
def sass_css(path: str) -> SafeString:
    """Return a `<link>` tag for one of your compiled CSS files.

    Examples::

        {% load sass %}
        {% sass_css "blog/css/site.css" %}  {# <link rel="stylesheet" href="/static/compiled_sass/scss/blog/css/site.css"> #}
    """
    return format_html('<link rel="stylesheet" href="{}">', sass_url(path))
