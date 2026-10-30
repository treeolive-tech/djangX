"""Rich console helpers with a shared, themed output style."""

from enum import StrEnum

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

__all__: list[str] = ["THEME", "Style", "console", "cprint"]


class Style(StrEnum):
    """Semantic style names, resolved to colours by :data:`THEME`.

    Examples::

        cprint("Failed", Style.ERROR)  # bold red
    """

    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"
    INFO = "info"
    DEBUG = "debug"
    HIGHLIGHT = "highlight"


THEME = Theme(
    styles={
        Style.ERROR: "bold red",
        Style.WARNING: "bold yellow",
        Style.SUCCESS: "bold green",
        Style.INFO: "bold cyan",
        Style.DEBUG: "bold magenta",
        Style.HIGHLIGHT: "bold blue",
    }
)

console = Console(theme=THEME)


def cprint(text: str | list[tuple[str, str]], style: str = "", end: str = "\n") -> None:
    """Print text, or ``(segment, style)`` pairs, in rich styles.

    Use ``""`` as the style for an unstyled segment.

    Examples::

        cprint("Build failed", Style.ERROR)
        cprint([("Copied ", Style.SUCCESS), ("a.txt", Style.HIGHLIGHT)])
    """
    segments = [(text, style)] if isinstance(text, str) else text
    console.print(Text.assemble(*segments), end=end)
