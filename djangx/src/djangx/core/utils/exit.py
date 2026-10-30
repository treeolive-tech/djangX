from enum import IntEnum

__all__: list[str] = ["ExitCode"]


class ExitCode(IntEnum):
    """Standard process exit codes following Unix conventions.

    Examples::

        raise SystemExit(ExitCode.ERROR)   # exits with code 1
        raise SystemExit(ExitCode.SUCCESS) # exits with code 0
    """

    SUCCESS = 0  # Command completed without errors.
    ERROR = 1  # Command encountered an error.
