from enum import IntEnum

__all__: list[str] = ["Exit"]


class Exit(IntEnum):
    """Standard process exit codes following Unix conventions.

    Examples::

        raise SystemExit(Exit.ERROR)   # exits with code 1
        raise SystemExit(Exit.SUCCESS) # exits with code 0
    """

    SUCCESS = 0
    ERROR = 1
