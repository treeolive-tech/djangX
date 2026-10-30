from enum import IntEnum

__all__: list[str] = ["Exit", "Verbosity"]


class Exit(IntEnum):
    """Standard process exit codes following Unix conventions.

    Examples::

        raise SystemExit(ExitCode.ERROR)   # exits with code 1
        raise SystemExit(ExitCode.SUCCESS) # exits with code 0
    """

    SUCCESS = 0
    ERROR = 1


class Verbosity(IntEnum):
    """Django management command output levels."""

    QUIET = 0
    NORMAL = 1
    VERBOSE = 2
    VERY_VERBOSE = 3
