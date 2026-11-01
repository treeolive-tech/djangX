"""Template tags for linking the project's compiled Sass output."""

from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import SafeString

from ..utils.sass import Sass

register = template.Library()


@register.simple_tag
def custom_css_url() -> str:
    """Return the static URL of the compiled CSS.

    Examples::

        {% custom_css_url %}  {# /static/vendor/bootstrap/css/custom.css #}
    """
    return static(f"{Sass.CSS_STATIC_DIR}/{Sass.CSS_FILE}")


@register.simple_tag
def custom_css() -> SafeString:
    """Return a `<link>` tag for the compiled CSS.

    Examples::

        {% load sass %}
        {% custom_css %}  {# <link rel="stylesheet" href="/static/..."> #}
    """
    return format_html('<link rel="stylesheet" href="{}">', custom_css_url())
