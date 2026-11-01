"""``djx platform``: print the OS and CPU architecture.

Examples::

    $ djx platform
    OS:           linux
    Architecture: x64
"""

from ...utils.commands import NonSystemCheckedCommand
from ...utils.console import Style, cprint
from ...utils.platform import Platform


class Command(NonSystemCheckedCommand):
    """Print the OS and CPU architecture."""

    help = "Display platform information"

    def handle(self, *args, **options) -> None:
        """Detect the platform and print its OS and architecture."""
        platform = Platform()
        cprint([("OS:           ", Style.INFO), (platform.os_name, Style.HIGHLIGHT)])
        cprint(
            [("Architecture: ", Style.INFO), (platform.architecture, Style.HIGHLIGHT)]
        )
