"""Console helpers using Django's management command color styles."""

from enum import StrEnum
from os import environ

from django.core.management.color import make_style, no_style, supports_color

from .commands import Verbosity

__all__: list[str] = ["Style", "console", "cprint"]


class Style(StrEnum):
    """Semantic style names, resolved to Django management styles.

    Examples::

        cprint("Failed", Style.ERROR)  # bold red
    """

    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"
    INFO = "info"
    DEBUG = "debug"
    HIGHLIGHT = "highlight"


_DEFAULT_COLOR_SETTINGS = (
    "error=red,bold",
    "warning=yellow,bold",
    "success=green,bold",
    "http_info=cyan,bold",
    "sql_field=magenta,bold",
    "notice=blue,bold",
)

_color_settings = ";".join(_DEFAULT_COLOR_SETTINGS)
if custom_colors := environ.get("DJANGO_COLORS"):
    _color_settings = f"{_color_settings};{custom_colors}"

console = make_style(_color_settings) if supports_color() else no_style()
_STYLE_NAMES = {
    Style.ERROR: "ERROR",
    Style.WARNING: "WARNING",
    Style.SUCCESS: "SUCCESS",
    Style.INFO: "HTTP_INFO",
    Style.DEBUG: "SQL_FIELD",
    Style.HIGHLIGHT: "NOTICE",
}


def cprint(
    text: str | list[tuple[str, str]],
    style: str = "",
    end: str = "\n",
    *,
    verbosity: Verbosity = Verbosity.NORMAL,
    min_verbosity: Verbosity = Verbosity.NORMAL,
) -> None:
    """Print text, or ``(segment, style)`` pairs, in Django management styles.

    Use ``""`` as the style for an unstyled segment.

    Examples::

        cprint("Build failed", Style.ERROR)
        cprint([("Copied ", Style.SUCCESS), ("a.txt", Style.HIGHLIGHT)])
    """
    if verbosity < min_verbosity:
        return

    segments = [(text, style)] if isinstance(text, str) else text
    output = "".join(
        getattr(console, _STYLE_NAMES.get(segment_style, ""), lambda value: value)(
            segment
        )
        if segment_style
        else segment
        for segment, segment_style in segments
    )
    print(output, end=end)
