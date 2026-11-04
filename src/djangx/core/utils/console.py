# ramani: src/djangx/core/utils/console.py
"""Console helpers using Django's management command color styles."""

import sys
from enum import StrEnum
from os import environ
from typing import ClassVar

from django.core.management.color import color_style

from .commands import Verbosity

__all__: list[str] = ["Style", "console", "cprint"]


class Style(StrEnum):
    """Semantic style names; each value is a Django palette role.

    ``PLAIN`` applies no styling. Every other value is the role name used in
    ``DJANGO_COLORS`` (e.g. ``INFO`` is configured as ``http_info=...``).
    """

    PLAIN = "plain"
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"
    INFO = "http_info"
    DEBUG = "sql_field"
    HIGHLIGHT = "notice"


class _Console:
    COLORS: ClassVar[dict[Style, str]] = {
        Style.ERROR: "red,bold",
        Style.WARNING: "yellow,bold",
        Style.SUCCESS: "green,bold",
        Style.INFO: "cyan,bold",
        Style.DEBUG: "magenta,bold",
        Style.HIGHLIGHT: "blue,bold",
    }

    DJANGO_COLOR_DEFAULTS: ClassVar[str] = "dark;" + ";".join(
        f"{style}={spec}" for style, spec in COLORS.items()
    )

    def __init__(self) -> None:
        self._style = color_style()
        self._configured_colors: str | None = None
        self._configured_stream: object | None = None

    def _configure_django_colors(self) -> str:
        """Prepend our defaults to ``DJANGO_COLORS`` and return the result."""
        defaults = self.DJANGO_COLOR_DEFAULTS
        user_colors = environ.get("DJANGO_COLORS", "")
        if user_colors == defaults or user_colors.startswith(f"{defaults};"):
            return user_colors

        colors = f"{defaults};{user_colors}" if user_colors else defaults
        environ["DJANGO_COLORS"] = colors
        return colors

    def configure(self) -> None:
        colors = self._configure_django_colors()
        if colors == self._configured_colors and sys.stdout is self._configured_stream:
            return
        self._style.__dict__.update(color_style().__dict__)
        self._configured_colors = colors
        self._configured_stream = sys.stdout

    def apply(self, text: str, style: str) -> str:
        """Return ``text`` styled; plain or unknown styles are left as-is."""
        formatter = getattr(self._style, style.upper(), None)
        return formatter(text) if formatter else text


console = _Console()


def cprint(
    text: str | list[tuple[str, str]],
    style: str = Style.PLAIN,
    end: str = "\n",
    *,
    verbosity: Verbosity = Verbosity.NORMAL,
    min_verbosity: Verbosity = Verbosity.NORMAL,
) -> None:
    """Print text, or ``(segment, style)`` pairs, in Django management styles.

    Use ``Style.PLAIN`` for an unstyled segment.

    Examples::

        cprint("Failed", Style.ERROR)
        cprint([("Copied ", Style.SUCCESS), ("a.txt", Style.HIGHLIGHT)])
    """
    if verbosity < min_verbosity:
        return

    console.configure()
    segments = [(text, style)] if isinstance(text, str) else text
    print(
        "".join(console.apply(seg, seg_style) for seg, seg_style in segments), end=end
    )
