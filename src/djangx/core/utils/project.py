from pathlib import Path
from tomllib import load
from typing import Any

__all__: list[str] = ["DJANGO_SETTINGS_MODULE", "Project"]


class Project:
    def __init__(self, toml_path: Path | None = None) -> None:
        """Parse *toml_path*, or use empty data if it doesn't exist."""
        self.path: Path = toml_path or Path.cwd() / "pyproject.toml"
        self._data: dict[str, Any] = {}

        if self.path.is_file():
            with open(file=self.path, mode="rb") as f:
                self._data = load(f)

    def _get_str(self, *keys: str) -> str | None:
        """Return the string at *keys*, or ``None`` if missing or not a string.

        Examples::

            Project()._get_str("project", "name")  # "olyv"
            Project()._get_str("project", "version")  # None (not set)
        """
        value: Any = self._data
        for key in keys:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value if isinstance(value, str) else None

    @property
    def name(self) -> str:
        """The ``[project] name`` value.

        Raises:
            KeyError: If ``[project]`` or ``name`` is missing.
        """
        return self._data["project"]["name"]

    @property
    def description(self) -> str | None:
        """The ``[project] description`` value, or ``None`` if not a string."""
        return self._get_str("project", "description")

    @property
    def settings(self) -> str | None:
        """The ``[project] settings`` value, or ``None`` if not a string.

        Examples::

            Project().settings  # "app.settings"
        """
        return self._get_str("project", "settings")


DJANGO_SETTINGS_MODULE: str | None = Project().settings
