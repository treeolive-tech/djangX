# ramani: src/djangx/core/management/commands/random.py
from ...utils.commands import NonSystemCheckedCommand, Verbosity
from ...utils.console import Style, cprint
from ...utils.string import random_string


class Command(NonSystemCheckedCommand):
    """Generate a secure random string, print it and copy it to the clipboard.

    Examples::

        python manage.py random              # 50 characters, copied
        python manage.py random -l 32 --no-clipboard
    """

    help = "Random string generator"

    def add_arguments(self, parser) -> None:
        """Register ``--length`` and ``--no-clipboard``."""
        parser.add_argument(
            "-l",
            "--length",
            type=int,
            default=50,
            help="Number of characters to generate (default: 50).",
        )
        parser.add_argument(
            "--no-clipboard",
            action="store_true",
            help="Skip copying the generated string to the clipboard.",
        )

    def handle(self, *args, **options) -> None:
        """Print a random string, then copy it unless ``--no-clipboard`` is set."""
        random_str = random_string(length=options["length"])
        cprint([("✓ Generated: ", Style.SUCCESS), (random_str, Style.HIGHLIGHT)])

        if options["no_clipboard"]:
            return

        try:
            import pyperclip

            pyperclip.copy(random_str)
            cprint(
                "✓ Copied to clipboard!",
                Style.SUCCESS,
                verbosity=Verbosity(options["verbosity"]),
            )
        except Exception as e:  # noqa: BLE001  # non-fatal, string already shown
            cprint(f"Could not copy to clipboard: {e}", Style.WARNING)
