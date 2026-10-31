"""File, directory, and clipboard copy command.

Django management command: ``djx copy``

Copy a file::

    $ djx copy /path/to/file.txt /path/to/dest.txt
    ✓ File copied successfully from /path/to/file.txt to /path/to/dest.txt

Copy a directory::

    $ djx copy /path/to/src_dir /path/to/dest_dir
    ✓ Directory copied successfully from /path/to/src_dir to /path/to/dest_dir

Copy text to the clipboard (omit destination)::

    $ djx copy "some text"
    ✓ Copied to clipboard: some text
"""

from ...utils.commands import NonSystemCheckedCommand, Verbosity
from ...utils.copy import copy


class Command(NonSystemCheckedCommand):
    """Django management command: copy a file, directory, or text."""

    help = "Copy a file, directory, or text to the clipboard"

    def add_arguments(self, parser) -> None:
        """Register the ``source`` and optional ``destination`` arguments."""
        parser.add_argument(
            "source",
            type=str,
            help="Source file path, directory path, or text to copy to clipboard.",
        )
        parser.add_argument(
            "destination",
            # nargs="?" makes this a positional-but-optional argument.
            # When omitted by the user, options["destination"] will be None,
            # which triggers clipboard mode in the copy() utility.
            nargs="?",
            default=None,
            type=str,
            help="Destination path (omit to copy source text to clipboard instead).",
        )

    def handle(self, *args, **options) -> None:
        """Execute the copy operation.

        Django calls this after parsing the arguments.  Parsed values arrive
        in *options* as a dict keyed by argument name.

        Raises:
            SystemExit: With exit code 1 if the copy operation fails, so the
                        shell receives a non-zero exit code signalling failure.
        """
        source: str = options["source"]
        destination: str | None = options["destination"]

        success: bool = copy(
            source,
            destination,
            verbosity=Verbosity(options["verbosity"]),
        )

        if not success:
            from ...utils.exit import Exit

            raise SystemExit(Exit.ERROR)
