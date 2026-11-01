"""String and URL path helpers."""

import re
from collections.abc import Iterable
from string import ascii_letters, digits
from typing import Any

__all__: list[str] = ["max_length_from_choices", "normalize_url_path", "random_string"]


def random_string(length: int = 16) -> str:
    """Return a cryptographically secure random string of letters and digits.

    Examples::

        random_string()  # "aB3dEf7gHi9jKl2m"
        random_string(32)  # a 32-character string
    """
    from django.utils.crypto import get_random_string

    return get_random_string(length=length, allowed_chars=ascii_letters + digits)


def max_length_from_choices(choices: Iterable[tuple[str, Any]]) -> int:
    """Return the length of the longest stored value in `choices`, or ``0`` if empty.

    Examples::

        max_length_from_choices([("pending", "Pending"), ("archived", "Archived")])  # 8
        max_length_from_choices([(s.value, s.name) for s in Status])  # for a StrEnum
        max_length_from_choices([])  # 0
    """
    return max((len(value) for value, _ in choices), default=0)


def normalize_url_path(
    url: str, leading_slash: bool = False, trailing_slash: bool = True
) -> str:
    """Collapse repeated slashes and set the leading/trailing slash; empty gives ``"/"``.

    Examples::

        normalize_url_path("api//v1//users/")  # "api/v1/users/"
        normalize_url_path("/api/v1", leading_slash=True)  # "/api/v1/"
        normalize_url_path("api/v1/", trailing_slash=False)  # "api/v1"
        normalize_url_path("")  # "/"
    """
    url = re.sub(r"/{2,}", "/", url)
    url = f"/{url.lstrip('/')}" if leading_slash else url.lstrip("/")
    url = f"{url.rstrip('/')}/" if trailing_slash else url.rstrip("/")
    return url or "/"
