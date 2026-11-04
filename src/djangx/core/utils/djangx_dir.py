# ramani: src/djangx/core/utils/djangx_dir.py
"""djangX's per-project working folder, `.djangx`."""

from pathlib import Path
from typing import ClassVar, final

__all__: list[str] = ["DjangxDir"]


@final
class DjangxDir:
    """The `.djangx` folder in a project: generated files that must not be committed.

    Parts of djangX that need somewhere to put generated files use subfolders of it:

    - `static/`: generated static files, served and collected through
      `STATICFILES_DIRS` (see `Conf.staticfiles_dirs`). Always created, so
      `STATICFILES_DIRS` never points at a missing folder
    - other folders for features' own bookkeeping, such as `sass/` build stamps,
      created by whatever needs them

    The folder gets a `.gitignore` containing `*`, so nothing in it is committed.
    The location is `BASE_DIR / ".djangx"`.

    Examples::

        DjangxDir.path()  # Path("/srv/site/.djangx")
        DjangxDir.static_dir()  # Path("/srv/site/.djangx/static")
        DjangxDir.ensure()  # creates .djangx and its .gitignore if missing
    """

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    NAME: ClassVar[str] = ".djangx"

    @classmethod
    def path(cls, base_dir: Path | None = None) -> Path:
        """Return the `.djangx` folder inside `base_dir`.

        Without `base_dir` this uses `settings.BASE_DIR` (or the working directory if
        the project doesn't define it). Pass `base_dir` while settings are still being
        loaded, when `django.conf.settings` can't be read yet.
        """
        if base_dir is None:
            from django.conf import settings

            base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        return Path(base_dir) / cls.NAME

    @classmethod
    def static_dir(cls, base_dir: Path | None = None) -> Path:
        """Return `.djangx/static`, where generated static files are written."""
        return cls.path(base_dir) / "static"

    @classmethod
    def ensure(cls, base_dir: Path | None = None) -> Path:
        """Create `.djangx`, its `static/` folder and its `.gitignore` if missing.

        Returns the `.djangx` folder. An existing `.gitignore` is never changed, so you
        can adjust it if you want. Raises `OSError` if the folders can't be created.
        """
        root = cls.path(base_dir)
        cls.static_dir(base_dir).mkdir(parents=True, exist_ok=True)
        try:
            with (root / ".gitignore").open("x", encoding="utf-8") as file:
                file.write("*\n")
        except FileExistsError:
            pass
        return root
