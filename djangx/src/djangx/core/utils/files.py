"""Templates and the single writer for `manage.py`, `asgi.py` and `wsgi.py`."""

from pathlib import Path
from typing import Literal

Result = Literal["wrote", "same", "differs"]

MANAGE_PY: str = '''\
"""Vercel reads this for the settings module. For development, run `djangx` or `djx` instead."""

from os import environ

from djangx.core.utils import DJANGO_SETTINGS_MODULE

assert DJANGO_SETTINGS_MODULE is not None
environ.setdefault(key="DJANGO_SETTINGS_MODULE", value=DJANGO_SETTINGS_MODULE)

if __name__ == "__main__":
    from sys import argv

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)
'''

ENTRYPOINT: str = """\
from os import environ

from django.core.{kind} import get_{kind}_application
from djangx.core.utils import DJANGO_SETTINGS_MODULE

assert DJANGO_SETTINGS_MODULE is not None
environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)
application = get_{kind}_application()
"""

TEMPLATES: dict[str, str] = {
    "manage": MANAGE_PY,
    "asgi": ENTRYPOINT.format(kind="asgi"),
    "wsgi": ENTRYPOINT.format(kind="wsgi"),
}


def write_file(kind: str, dir: Path, *, overwrite: bool = False) -> Result:
    """Write `dir/<kind>.py`; an existing file is kept unless `overwrite`.

    Examples::

        write_file("wsgi", APP_DIR)  # "wrote"
        write_file("wsgi", APP_DIR)  # "same" (already there, matches the template)
        write_file("manage", BASE_DIR)  # "differs" (user edited it; left alone)
        write_file("manage", BASE_DIR, overwrite=True)  # "wrote"
    """
    file = dir / f"{kind}.py"
    text = TEMPLATES[kind]
    if file.exists() and not overwrite:
        return "same" if file.read_text() == text else "differs"
    dir.mkdir(parents=True, exist_ok=True)
    file.write_text(text)
    return "wrote"
